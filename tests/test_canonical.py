import datetime
import math
import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "parser"))

from canonical import (  # noqa: E402
    CanonicalizationError,
    CyclicValueError,
    FrozenCanonicalSet,
    InvalidUnicodeError,
    canonical_document,
    canonical_json,
    canonical_value,
    decode_canonical_document,
    jcs_dumps,
    normalize_acyclic,
    relationship_id,
    relationship_key,
)


class CanonicalValueTests(unittest.TestCase):
    def test_authored_wrapper_shape_cannot_collide_with_tagged_date(self):
        tagged_date = {"v": datetime.date(2026, 8, 23)}
        authored_mapping = {
            "v": {"$yamlType": "date", "value": "2026-08-23"}
        }

        self.assertNotEqual(
            canonical_json(tagged_date), canonical_json(authored_mapping)
        )
        self.assertIn('["date","2026-08-23"]', canonical_json(tagged_date))
        self.assertIn('["string","$yamlType"]', canonical_json(authored_mapping))

    def test_all_values_are_tagged_and_mapping_order_is_irrelevant(self):
        first = {"z": [None, True], "a": {"x": "text"}}
        second = {"a": {"x": "text"}, "z": [None, True]}

        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(canonical_value(None), ["null"])
        self.assertEqual(canonical_value(True), ["bool", True])
        self.assertEqual(canonical_value("x"), ["string", "x"])

    def test_numeric_equivalence_and_kind_distinctions(self):
        self.assertEqual(canonical_json(1), canonical_json(1.0))
        self.assertEqual(canonical_json(Decimal("0.5")), canonical_json(Fraction(1, 2)))
        self.assertEqual(canonical_json(-0.0), canonical_json(0))
        self.assertNotEqual(canonical_json(True), canonical_json(1))
        self.assertNotEqual(canonical_json("1"), canonical_json(1))
        self.assertEqual(canonical_value(2**80), ["number", str(2**80)])
        self.assertEqual(canonical_value(0.5), ["number", "1/2"])
        self.assertEqual(canonical_value(float("nan")), ["number", "nan"])
        self.assertEqual(canonical_value(float("inf")), ["number", "+inf"])
        self.assertEqual(canonical_value(float("-inf")), ["number", "-inf"])

    def test_binary_set_sequence_date_and_timestamp_are_distinct(self):
        values = [
            b"Hello",
            {"one", "two"},
            ["one", "two"],
            datetime.date(2026, 8, 23),
            datetime.datetime(2026, 8, 23, 10, 30),
        ]

        encodings = {canonical_json(value) for value in values}
        self.assertEqual(len(encodings), len(values))
        self.assertEqual(canonical_value(b"Hello"), ["binary", "SGVsbG8="])

    def test_timestamps_with_equal_instants_are_equivalent(self):
        utc = datetime.datetime(
            2026, 8, 23, 10, 30, tzinfo=datetime.timezone.utc
        )
        plus_two = datetime.datetime(
            2026,
            8,
            23,
            12,
            30,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )

        self.assertEqual(canonical_json(utc), canonical_json(plus_two))
        self.assertEqual(canonical_value(utc), ["timestamp", "2026-08-23T10:30:00Z"])

    def test_acyclic_aliases_expand_by_value_and_cycles_are_rejected(self):
        shared = {"items": [1, 2]}
        aliased = {"a": shared, "b": shared}
        expanded = {"a": {"items": [1, 2]}, "b": {"items": [1, 2]}}

        normalized = normalize_acyclic(aliased)
        self.assertEqual(normalized, expanded)
        self.assertIsNot(normalized["a"], normalized["b"])
        self.assertEqual(canonical_json(aliased), canonical_json(expanded))

        self_cycle = []
        self_cycle.append(self_cycle)
        with self.assertRaises(CyclicValueError):
            normalize_acyclic(self_cycle)
        with self.assertRaises(CyclicValueError):
            canonical_json(self_cycle)

        left = {}
        right = {"left": left}
        left["right"] = right
        with self.assertRaises(CyclicValueError):
            canonical_json(left)

    def test_sets_are_order_independent(self):
        self.assertEqual(
            canonical_json(frozenset(["z", "a"])),
            canonical_json(set(["a", "z"])),
        )

    def test_set_decode_preserves_python_colliding_pgm_values(self):
        document = [
            "pgm-yaml",
            "v1",
            ["set", [["bool", True], ["number", "1"]]],
        ]

        decoded = decode_canonical_document(document)

        self.assertIsInstance(decoded, FrozenCanonicalSet)
        self.assertEqual(len(decoded), 2)
        self.assertIn(True, decoded)
        self.assertIn(1, decoded)
        self.assertEqual(canonical_document(decoded), document)


class JcsSubsetTests(unittest.TestCase):
    def test_object_keys_use_jcs_utf16_order(self):
        supplementary = "\U00010000"
        bmp_private_use = "\ue000"

        encoded = jcs_dumps({bmp_private_use: "bmp", supplementary: "supplementary"})
        self.assertEqual(
            encoded,
            '{"\U00010000":"supplementary","\ue000":"bmp"}',
        )

    def test_unicode_is_preserved_without_normalization(self):
        composed = "\u00e9"
        decomposed = "e\u0301"

        self.assertNotEqual(canonical_json(composed), canonical_json(decomposed))
        self.assertIn(composed, canonical_json(composed))

    def test_lone_surrogates_are_rejected_everywhere(self):
        invalid = "\ud800"

        with self.assertRaises(InvalidUnicodeError):
            canonical_json(invalid)
        with self.assertRaises(InvalidUnicodeError):
            jcs_dumps({invalid: "key"})
        with self.assertRaises(InvalidUnicodeError):
            relationship_key(invalid, "target", {})

    def test_json_number_tokens_are_not_in_the_supported_jcs_subset(self):
        with self.assertRaises(CanonicalizationError):
            jcs_dumps({"number": 1})

    def test_nonfinite_values_are_strings_not_json_numbers(self):
        for value in (math.nan, math.inf, -math.inf):
            encoded = canonical_json(value)
            self.assertNotIn("NaN", encoded)
            self.assertNotIn("Infinity", encoded)


class RelationshipIdentifierTests(unittest.TestCase):
    def test_semantic_key_is_stable_and_occurrence_ids_are_distinct(self):
        first_key = relationship_key(
            "people/Ada", "places/London", {"type": "born_in", "year": 1815}
        )
        second_key = relationship_key(
            "people/Ada", "places/London", {"year": 1815.0, "type": "born_in"}
        )

        self.assertEqual(first_key, second_key)
        self.assertRegex(first_key, r"^pgmkey:v1:sha256:[0-9a-f]{64}$")
        self.assertEqual(
            first_key,
            "pgmkey:v1:sha256:"
            "afaf816b63caf85ec2ed5b299d229e6fc52c864b1f50c8d95806106de2b628ab",
        )

        first_id = relationship_id(first_key, 0)
        second_id = relationship_id(first_key, 1)
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(first_id, relationship_id(first_key, 0))
        self.assertRegex(first_id, r"^pgmrel:v1:sha256:[0-9a-f]{64}$")
        self.assertEqual(
            first_id,
            "pgmrel:v1:sha256:"
            "f32b404e8497ddcfddb32419f8e0bf973b4dccc5a29e06841fe0e7ada8459451",
        )
        self.assertEqual(
            second_id,
            "pgmrel:v1:sha256:"
            "bab2e98c69a348eaea714c52863e4e69fcb82990c24ddbbc98e558ebf55fa5df",
        )

    def test_key_changes_with_each_semantic_component(self):
        baseline = relationship_key("a", "b", {"type": "r"})

        self.assertNotEqual(baseline, relationship_key("x", "b", {"type": "r"}))
        self.assertNotEqual(baseline, relationship_key("a", "x", {"type": "r"}))
        self.assertNotEqual(baseline, relationship_key("a", "b", {"type": "x"}))

    def test_occurrence_ordinal_is_zero_based_and_validated(self):
        key = relationship_key("a", "b", {})

        relationship_id(key, 0)
        for invalid in (-1, True, 1.5, "0"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    relationship_id(key, invalid)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
