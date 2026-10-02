# PGM OKF Relationship Trust Profile v1 Public Draft

This optional profile gives each Property Graph Markdown Relationship occurrence
an advisory trust tier using the event vocabulary and three-tier derivation of
Open Knowledge Format (OKF). It lets a consumer distinguish an unverified Link
assertion from one confirmed by a machine or a person without moving that
assertion out of the Markdown body. The complete authored YAML Properties remain
the source; the tier is a derived view, not a new authored Property.

This is a draft profile for implementation and discussion, not an accepted OKF
extension. It applies to PGM Core Results as defined by the repository's
[`SPEC.md`](../../SPEC.md), which pins an exact OKF 0.2 specification in §1.1.
It does not change PGM Core conformance, the PGM JSON Exchange Profile v1, or
the physical direction of a Markdown Link.

## Normative terms and scope

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are interpreted as
described in PGM §1. Every PGM Core Relationship occurrence is evaluated
independently, including untyped Relationships, repeated Links, and Links to
absent target Concepts. Its input is the complete top-level Property map
parsed from that one Link title under PGM §5.3. No Concept frontmatter field or
other Link occurrence supplies an event for it.

The name `verified` and its event shape are reused from the pinned OKF §5.2.
For Relationships it is interpreted only by a processor that claims this
profile. `generated` remains an authored PGM Property but is neither a tier
input nor validated by this profile. All other Relationship Properties,
including `type`, `direction`, and `confidence`, remain available but do not
affect the tier.

Profile support is optional for PGM Core consumers. A consumer that presents
Relationship trust SHOULD use this profile and derive its tiers only from the
specified `verified` events, matching OKF's consumer guidance in §11. A
consumer that does not present Relationship trust may still read and preserve
the complete `verified` Property without claiming this profile.

## Verification event validation

If `verified` is present, its value MUST be either one event Mapping or a
non-empty Sequence of event Mappings. A bare Mapping is evaluated as a
one-element Sequence, following OKF §5.2. Every verification event MUST have
both a `by` actor and an `at` datetime. A valid actor uses one of these OKF §7
forms, with non-empty components: `<producer>/<version>`, `process:<id>`, or
`human:<id>`. A valid `at` is an ISO 8601 datetime with an explicit UTC offset,
written as a YAML string or an explicitly tagged, timezone-aware YAML
`!!timestamp`. String values use the portable form
`YYYY-MM-DDThh:mm[:ss[.fraction]](Z|+hh:mm|-hh:mm)` and MUST represent a valid
calendar datetime. Other keys in an event Mapping are retained without
changing the tier.

The explicit-offset and non-empty-event requirements make this optional
profile's result portable and unambiguous. They are profile checks, not new
PGM Core requirements. A present `verified: null`, empty Sequence, invalid
actor, or missing or invalid required datetime MUST produce a profile error;
it MUST NOT be treated as absent `verified`.

## Tier derivation

For each occurrence without a profile error, a profile processor MUST derive
exactly one tier from that occurrence's `verified` value:

1. If `verified` is absent, the tier is `unverified`.
2. If `verified` contains only non-`human:` actors, the tier is
   `machine-confirmed`.
3. If at least one verifier is a `human:<id>` actor, the tier is
   `human-reviewed`.

`generated` never raises the tier, regardless of its value. The source or
target Concept's OKF tier is not inherited by the Relationship. Two identical
Link occurrences are evaluated separately, even when they share a semantic
Relationship key. Neither `confidence` nor `direction` changes the tier. The YAML
`direction: inbound` Property does not reverse the physical PGM Core edge:
that edge remains from the containing Concept to the Link destination.

The derived tier MUST NOT be inserted into the authored Property map or the
PGM JSON Exchange v1 Relationship object. A consumer MAY present it in a
separate view or report alongside the complete Properties.

## Profile errors and conformance

A processor claiming **PGM OKF Relationship Trust Profile v1** MUST evaluate
every occurrence in a conforming PGM Core Result and identify this profile in
its conformance statement together with the PGM Core version, pinned OKF
commit and specification hash, and processor name and version. It MUST produce
the tiers above for valid events. For an occurrence with invalid present
verification events, it MUST report a distinct profile error and an
unavailable tier. It MUST NOT silently downgrade the
occurrence to `unverified`, remove it, rewrite its Properties, or turn the
profile error into a PGM Core Bundle error. A bundle can therefore conform to
PGM Core while failing this optional profile.

An unusable brace-leading Link title follows PGM §5.5: the Core occurrence
remains with an empty Property map and a warning. In this profile, that
occurrence has no parsed `verified` Property and is `unverified`; the Core
warning remains visible so a consumer does not mistake a failed annotation
for a cleanly authored one.

## Security and occurrence identity

The three tiers are advisory, as in OKF §5.3. A `by` string declares an actor
but does not authenticate that actor. This profile does not define signatures,
authorization, access control, or automatic invalidation of a verification
after a later edit. `generated.at` and `verified` remain independent, as in
OKF §5.2; consumers MAY separately display event recency, subject to any
separate validation they apply to `generated`.

PGM §6 derives portable Relationship keys and occurrence IDs from the complete
Property map. Adding or changing `verified` therefore changes those technical
identifiers, and may change duplicate-occurrence ordinals. The tier is derived
from the current Link occurrence in the current bundle snapshot. These IDs
MUST NOT be presented as durable identities for an evolving business claim or
as proof that an earlier verification still covers modified Properties.

## Example

The containing Concept may be human-reviewed while its first Link remains
unverified:

```markdown
---
type: Function
verified: {by: 'human:reviewer', at: '2026-09-01T08:00:00Z'}
---

- [handler](handler.md "{type: calls, generated: {by: 'roteiro/5.0.0', at: '2026-09-01T12:00:00Z'}}")
- [reviewed handler](handler.md "{type: calls, verified: {by: 'human:alice', at: '2026-09-02T09:00:00Z'}}")
```

The first Relationship is `unverified` despite its source Concept's
verification and its own `generated` event. The second is `human-reviewed`.
Both still have their complete authored Properties and both physically point
from this Concept to `handler`. The executable
[interoperability example](../../interop/okf-relationship-carriers/README.md)
also covers repeated Links, non-human verification, and a separate proposed
frontmatter authoring model from OKF issue #16.
