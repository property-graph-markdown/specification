"""Canonical PGM value encoding and Relationship identifiers.

The encoding is deliberately independent of JSON's native object and number
model.  Every YAML value is tagged, mappings are represented as sorted entry
arrays, and all numeric payloads are strings.  Consequently an authored YAML
mapping can never be confused with an encoding envelope and integers are not
limited to JSON's interoperable numeric range.

Canonical PGM value encoding v1 has this JSON-compatible shape::

    ["pgm-yaml", "v1", tagged-value]

where ``tagged-value`` is one of::

    ["null"]
    ["bool", true | false]
    ["number", canonical-rational | "nan" | "+inf" | "-inf"]
    ["string", unicode-string]
    ["binary", canonical-base64]
    ["date", "YYYY-MM-DD"]
    ["timestamp", canonical-ISO-8601]
    ["sequence", [tagged-value, ...]]
    ["mapping", [[tagged-key, tagged-value], ...]]
    ["set", [tagged-value, ...]]

A finite number is a reduced rational string: ``n`` when its denominator is
one, otherwise ``n/d`` with a positive denominator.  This makes numerically
equal integers and floating-point values canonicalize equally while retaining
the distinction between booleans and numbers.

The serialized form is the RFC 8785 (JCS) subset needed by the tagged model:
null, booleans, Unicode strings, arrays, and string-keyed objects.  JSON number
tokens are intentionally rejected.  This small implementation still follows
JCS's UTF-16 object-key ordering and Unicode validity requirements exactly.
"""

from __future__ import annotations

import base64
import binascii
import datetime as _datetime
import hashlib
import json
import math
import re
from collections.abc import Mapping, Set as AbstractSet
from decimal import Decimal
from fractions import Fraction
from typing import Any


ENCODING_NAME = "pgm-yaml"
ENCODING_VERSION = "v1"
RELATIONSHIP_KEY_DOMAIN = "pgm-relationship-key"
RELATIONSHIP_ID_DOMAIN = "pgm-relationship-id"
RELATIONSHIP_KEY_PREFIX = "pgmkey:v1:sha256:"
RELATIONSHIP_ID_PREFIX = "pgmrel:v1:sha256:"
CANONICAL_NUMBER_RE = re.compile(
    r"^(?:0|-?[1-9][0-9]*|-?[1-9][0-9]*/(?:[2-9]|[1-9][0-9]+)|nan|\+inf|-inf)$"
)


class CanonicalizationError(ValueError):
    """Base class for values that cannot be canonically represented."""


class CyclicValueError(CanonicalizationError):
    """Raised when a YAML alias graph contains a cycle."""


class InvalidUnicodeError(CanonicalizationError):
    """Raised when a string contains a lone UTF-16 surrogate code point."""


class DuplicateCanonicalKeyError(CanonicalizationError):
    """Raised when distinct mapping keys have the same canonical value."""


class UnsupportedValueError(CanonicalizationError):
    """Raised for values outside the PGM canonical value domain."""


class FrozenMapping(Mapping[Any, Any]):
    """Hashable immutable Mapping used when a YAML Mapping is itself a key.

    Python ``dict`` cannot represent Mapping-valued keys and also conflates
    some PGM-distinct keys such as ``true`` and ``1``.  This small value object
    keeps the canonical entry sequence so those valid nested YAML mappings can
    survive JSON import and re-export without narrowing the PGM value model.
    """

    __slots__ = ("_entries",)

    def __init__(self, entries: Any):
        self._entries = tuple((key, value) for key, value in entries)

    def __iter__(self):
        return (key for key, _ in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, key: Any) -> Any:
        encoded = jcs_bytes(canonical_value(key))
        for candidate, value in self._entries:
            if jcs_bytes(canonical_value(candidate)) == encoded:
                return value
        raise KeyError(key)

    def items(self):
        return self._entries

    def __hash__(self) -> int:
        digest = hashlib.sha256(canonical_bytes(self)).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FrozenMapping):
            return NotImplemented
        return canonical_value(self) == canonical_value(other)


class FrozenCanonicalSet(AbstractSet[Any]):
    """Immutable Set whose membership follows canonical PGM value identity.

    Python's native sets conflate values that PGM keeps distinct, notably
    ``true`` and ``1``.  Decoding into this representation preserves every
    canonical entry, including otherwise-unhashable YAML collection values,
    so a JSON import can be re-exported without loss.
    """

    __slots__ = ("_items", "_encoded_items")

    def __init__(self, items: Any):
        encoded_items = [
            (jcs_bytes(canonical_value(item)), item) for item in items
        ]
        encoded_items.sort(key=lambda entry: entry[0])
        previous: bytes | None = None
        for encoded, _ in encoded_items:
            if encoded == previous:
                raise DuplicateCanonicalKeyError(
                    "canonical set contains duplicate semantic values"
                )
            previous = encoded
        self._items = tuple(item for _, item in encoded_items)
        self._encoded_items = tuple(encoded for encoded, _ in encoded_items)

    def __contains__(self, value: object) -> bool:
        try:
            encoded = jcs_bytes(canonical_value(value))
        except CanonicalizationError:
            return False
        return encoded in self._encoded_items

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        digest = hashlib.sha256(canonical_bytes(self)).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FrozenCanonicalSet):
            return NotImplemented
        return canonical_value(self) == canonical_value(other)


def normalize_acyclic(value: Any) -> Any:
    """Return an acyclic value copy, expanding shared alias subgraphs.

    Alias identity and anchor names are YAML presentation details and therefore
    do not affect PGM value identity.  A repeated, acyclic object is copied at
    each occurrence.  Re-entering an object on the active recursion stack is a
    semantic cycle and raises :class:`CyclicValueError`.
    """

    return _copy_acyclic(value, set())


def canonical_value(value: Any) -> list[Any]:
    """Return the fully tagged JSON-compatible representation of ``value``."""

    return _encode_value(value, set())


def canonical_document(value: Any) -> list[Any]:
    """Return the self-describing PGM canonical value document."""

    return [ENCODING_NAME, ENCODING_VERSION, canonical_value(value)]


def canonical_json(value: Any) -> str:
    """Return canonical PGM value encoding v1 serialized with JCS."""

    return jcs_dumps(canonical_document(value))


def canonical_bytes(value: Any) -> bytes:
    """Return UTF-8 bytes of :func:`canonical_json`, without BOM or newline."""

    return canonical_json(value).encode("utf-8")


def decode_canonical_document(document: Any) -> Any:
    """Decode and validate one canonical PGM value encoding v1 document.

    Validation is intentionally stricter than accepting a merely similar
    tagged tree: decoding followed by canonical re-encoding MUST reproduce the
    input document exactly.  This rejects unsorted mappings and sets,
    non-canonical rational numbers, duplicate semantic keys, and malformed
    scalar payloads.
    """

    if (
        not isinstance(document, list)
        or len(document) != 3
        or document[0] != ENCODING_NAME
        or document[1] != ENCODING_VERSION
    ):
        raise CanonicalizationError(
            'canonical document must be ["pgm-yaml", "v1", tagged-value]'
        )
    decoded = _decode_value(document[2], key_context=False)
    if canonical_document(decoded) != document:
        raise CanonicalizationError("PGM value document is not in canonical form")
    return decoded


def relationship_key(source: str, target: str, properties: Any) -> str:
    """Return the semantic Relationship key for source, target, and Properties."""

    _validate_unicode(source)
    _validate_unicode(target)
    preimage = [
        RELATIONSHIP_KEY_DOMAIN,
        ENCODING_VERSION,
        source,
        target,
        canonical_document(properties),
    ]
    digest = hashlib.sha256(jcs_bytes(preimage)).hexdigest()
    return RELATIONSHIP_KEY_PREFIX + digest


def relationship_id(key: str, occurrence_ordinal: int) -> str:
    """Return an occurrence ID from a semantic key and zero-based ordinal.

    The ordinal counts earlier Relationships with the same semantic key in
    Markdown source order.  It is intentionally encoded as a decimal string so
    the hash preimage never depends on a JSON implementation's number model.
    """

    if not isinstance(key, str) or not key.startswith(RELATIONSHIP_KEY_PREFIX):
        raise ValueError("key must be a PGM v1 Relationship key")
    _validate_unicode(key)
    if (
        isinstance(occurrence_ordinal, bool)
        or not isinstance(occurrence_ordinal, int)
        or occurrence_ordinal < 0
    ):
        raise ValueError("occurrence ordinal must be a non-negative integer")
    preimage = [
        RELATIONSHIP_ID_DOMAIN,
        ENCODING_VERSION,
        key,
        str(occurrence_ordinal),
    ]
    digest = hashlib.sha256(jcs_bytes(preimage)).hexdigest()
    return RELATIONSHIP_ID_PREFIX + digest


def jcs_dumps(value: Any) -> str:
    """Serialize the number-free RFC 8785 subset used by this module."""

    return _jcs_serialize(value, set())


def jcs_bytes(value: Any) -> bytes:
    """Return UTF-8 JCS bytes, without BOM or trailing newline."""

    return jcs_dumps(value).encode("utf-8")


def _encode_value(value: Any, active: set[int]) -> list[Any]:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, (int, float, Decimal, Fraction)):
        return ["number", _canonical_number(value)]
    if isinstance(value, str):
        _validate_unicode(value)
        return ["string", value]
    if isinstance(value, (bytes, bytearray)):
        encoded = base64.b64encode(bytes(value)).decode("ascii")
        return ["binary", encoded]
    if isinstance(value, _datetime.datetime):
        return ["timestamp", _canonical_datetime(value)]
    if isinstance(value, _datetime.date):
        return ["date", value.isoformat()]
    if isinstance(value, Mapping):
        return _encode_mapping(value, active)
    if isinstance(value, (list, tuple)):
        object_id = _enter(value, active)
        try:
            return ["sequence", [_encode_value(item, active) for item in value]]
        finally:
            active.remove(object_id)
    if isinstance(value, (set, frozenset, FrozenCanonicalSet)):
        object_id = _enter(value, active)
        try:
            encoded_items = [_encode_value(item, active) for item in value]
            encoded_items.sort(key=jcs_bytes)
            _reject_duplicate_encodings(encoded_items, "set item")
            return ["set", encoded_items]
        finally:
            active.remove(object_id)
    raise UnsupportedValueError(
        f"unsupported canonical PGM value type: {type(value).__name__}"
    )


def _encode_mapping(value: Mapping[Any, Any], active: set[int]) -> list[Any]:
    object_id = _enter(value, active)
    try:
        entries = [
            [_encode_value(key, active), _encode_value(item, active)]
            for key, item in value.items()
        ]
        entries.sort(key=lambda entry: jcs_bytes(entry[0]))
        previous: bytes | None = None
        for key, _ in entries:
            encoded_key = jcs_bytes(key)
            if encoded_key == previous:
                raise DuplicateCanonicalKeyError(
                    "mapping contains canonically equivalent keys"
                )
            previous = encoded_key
        return ["mapping", entries]
    finally:
        active.remove(object_id)


def _canonical_number(value: int | float | Decimal | Fraction) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "+inf" if value > 0 else "-inf"
    if isinstance(value, Decimal):
        if value.is_nan():
            return "nan"
        if value.is_infinite():
            return "+inf" if value > 0 else "-inf"

    fraction = value if isinstance(value, Fraction) else Fraction(value)
    numerator = fraction.numerator
    denominator = fraction.denominator
    if numerator == 0:
        return "0"
    if denominator == 1:
        return str(numerator)
    return f"{numerator}/{denominator}"


def _canonical_datetime(value: _datetime.datetime) -> str:
    try:
        offset = value.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise UnsupportedValueError("invalid timezone-aware timestamp") from exc
    suffix = ""
    canonical = value
    if offset is not None:
        try:
            canonical = value.astimezone(_datetime.timezone.utc).replace(tzinfo=None)
        except (OverflowError, ValueError) as exc:
            raise UnsupportedValueError(
                "timestamp UTC normalization is outside years 0001 through 9999"
            ) from exc
        suffix = "Z"

    result = (
        f"{canonical.year:04d}-{canonical.month:02d}-{canonical.day:02d}"
        f"T{canonical.hour:02d}:{canonical.minute:02d}:{canonical.second:02d}"
    )
    if canonical.microsecond:
        fraction = f"{canonical.microsecond:06d}".rstrip("0")
        result += f".{fraction}"
    return result + suffix


def _decode_value(encoded: Any, *, key_context: bool) -> Any:
    if not isinstance(encoded, list) or not encoded or not isinstance(encoded[0], str):
        raise CanonicalizationError("tagged PGM value must be a non-empty JSON array")
    tag = encoded[0]

    if tag == "null":
        _require_tag_length(encoded, 1)
        return None
    if tag == "bool":
        _require_tag_length(encoded, 2)
        if not isinstance(encoded[1], bool):
            raise CanonicalizationError("bool payload must be a JSON boolean")
        return encoded[1]
    if tag == "number":
        _require_tag_length(encoded, 2)
        payload = encoded[1]
        if not isinstance(payload, str) or not CANONICAL_NUMBER_RE.fullmatch(payload):
            raise CanonicalizationError("invalid canonical number payload")
        if payload == "nan":
            return float("nan")
        if payload == "+inf":
            return float("inf")
        if payload == "-inf":
            return float("-inf")
        if "/" in payload:
            numerator, denominator = payload.split("/", 1)
            return Fraction(int(numerator), int(denominator))
        return int(payload)
    if tag == "string":
        _require_tag_length(encoded, 2)
        if not isinstance(encoded[1], str):
            raise CanonicalizationError("string payload must be a JSON string")
        _validate_unicode(encoded[1])
        return encoded[1]
    if tag == "binary":
        _require_tag_length(encoded, 2)
        payload = encoded[1]
        if not isinstance(payload, str):
            raise CanonicalizationError("binary payload must be a JSON string")
        try:
            return base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise CanonicalizationError("invalid canonical base64 payload") from exc
    if tag == "date":
        _require_tag_length(encoded, 2)
        try:
            return _datetime.date.fromisoformat(encoded[1])
        except (TypeError, ValueError) as exc:
            raise CanonicalizationError("invalid canonical date payload") from exc
    if tag == "timestamp":
        _require_tag_length(encoded, 2)
        payload = encoded[1]
        if not isinstance(payload, str):
            raise CanonicalizationError("timestamp payload must be a JSON string")
        normalized = payload[:-1] + "+00:00" if payload.endswith("Z") else payload
        try:
            return _datetime.datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise CanonicalizationError("invalid canonical timestamp payload") from exc
    if tag == "sequence":
        _require_tag_length(encoded, 2)
        if not isinstance(encoded[1], list):
            raise CanonicalizationError("sequence payload must be a JSON array")
        items = [
            _decode_value(item, key_context=key_context) for item in encoded[1]
        ]
        return tuple(items) if key_context else items
    if tag == "mapping":
        _require_tag_length(encoded, 2)
        if not isinstance(encoded[1], list):
            raise CanonicalizationError("mapping payload must be a JSON array")
        entries = []
        encoded_keys = set()
        for entry in encoded[1]:
            if not isinstance(entry, list) or len(entry) != 2:
                raise CanonicalizationError(
                    "canonical mapping entry must contain one key and value"
                )
            key = _decode_value(entry[0], key_context=True)
            item = _decode_value(entry[1], key_context=False)
            encoded_key = jcs_bytes(entry[0])
            if encoded_key in encoded_keys:
                raise DuplicateCanonicalKeyError(
                    "canonical mapping contains duplicate semantic keys"
                )
            encoded_keys.add(encoded_key)
            entries.append((key, item))
        if key_context:
            return FrozenMapping(entries)

        result = {}
        for key, item in entries:
            try:
                if key in result:
                    return FrozenMapping(entries)
                result[key] = item
            except TypeError:
                return FrozenMapping(entries)
        return result
    if tag == "set":
        _require_tag_length(encoded, 2)
        if not isinstance(encoded[1], list):
            raise CanonicalizationError("set payload must be a JSON array")
        items = [_decode_value(item, key_context=True) for item in encoded[1]]
        return FrozenCanonicalSet(items)
    raise CanonicalizationError(f"unknown canonical PGM value tag: {tag!r}")


def _require_tag_length(encoded: list[Any], length: int) -> None:
    if len(encoded) != length:
        raise CanonicalizationError(
            f"canonical {encoded[0]!r} value must contain {length} item(s)"
        )


def _copy_acyclic(value: Any, active: set[int]) -> Any:
    if value is None or isinstance(
        value,
        (bool, int, float, Decimal, Fraction, bytes, _datetime.date),
    ):
        return value
    if isinstance(value, bytearray):
        return bytearray(value)
    if isinstance(value, str):
        _validate_unicode(value)
        return value
    if isinstance(value, Mapping):
        object_id = _enter(value, active)
        try:
            entries = [
                (_copy_acyclic(key, active), _copy_acyclic(item, active))
                for key, item in value.items()
            ]
            if isinstance(value, FrozenMapping):
                return FrozenMapping(entries)
            result = {}
            for key, item in entries:
                try:
                    if key in result:
                        return FrozenMapping(entries)
                    result[key] = item
                except TypeError:
                    return FrozenMapping(entries)
            return result
        finally:
            active.remove(object_id)
    if isinstance(value, list):
        object_id = _enter(value, active)
        try:
            return [_copy_acyclic(item, active) for item in value]
        finally:
            active.remove(object_id)
    if isinstance(value, tuple):
        object_id = _enter(value, active)
        try:
            return tuple(_copy_acyclic(item, active) for item in value)
        finally:
            active.remove(object_id)
    if isinstance(value, FrozenCanonicalSet):
        object_id = _enter(value, active)
        try:
            return FrozenCanonicalSet(
                _copy_acyclic(item, active) for item in value
            )
        finally:
            active.remove(object_id)
    if isinstance(value, set):
        object_id = _enter(value, active)
        try:
            return {_copy_acyclic(item, active) for item in value}
        finally:
            active.remove(object_id)
    if isinstance(value, frozenset):
        object_id = _enter(value, active)
        try:
            return frozenset(_copy_acyclic(item, active) for item in value)
        finally:
            active.remove(object_id)
    raise UnsupportedValueError(
        f"unsupported canonical PGM value type: {type(value).__name__}"
    )


def _enter(value: Any, active: set[int]) -> int:
    object_id = id(value)
    if object_id in active:
        raise CyclicValueError("cyclic YAML alias graph is not canonicalizable")
    active.add(object_id)
    return object_id


def _reject_duplicate_encodings(values: list[Any], description: str) -> None:
    previous: bytes | None = None
    for value in values:
        encoded = jcs_bytes(value)
        if encoded == previous:
            raise DuplicateCanonicalKeyError(
                f"collection contains canonically equivalent {description}s"
            )
        previous = encoded


def _validate_unicode(value: str) -> None:
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise InvalidUnicodeError("lone UTF-16 surrogate is not valid JCS Unicode")


def _utf16_sort_key(value: str) -> bytes:
    _validate_unicode(value)
    return value.encode("utf-16-be")


def _jcs_serialize(value: Any, active: set[int]) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        _validate_unicode(value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (int, float, Decimal, Fraction)):
        raise CanonicalizationError(
            "JSON number tokens are outside the PGM JCS subset; encode as strings"
        )
    if isinstance(value, (list, tuple)):
        object_id = _enter(value, active)
        try:
            return "[" + ",".join(_jcs_serialize(item, active) for item in value) + "]"
        finally:
            active.remove(object_id)
    if isinstance(value, Mapping):
        object_id = _enter(value, active)
        try:
            if any(not isinstance(key, str) for key in value):
                raise CanonicalizationError("JCS object keys must be strings")
            keys = sorted(value, key=_utf16_sort_key)
            return "{" + ",".join(
                _jcs_serialize(key, active)
                + ":"
                + _jcs_serialize(value[key], active)
                for key in keys
            ) + "}"
        finally:
            active.remove(object_id)
    raise CanonicalizationError(
        f"value is outside the PGM JCS subset: {type(value).__name__}"
    )
