# OKF relationship-carrier interoperability exercise

This is an informative, executable comparison for [OKF issue #16](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/16), not an accepted OKF extension or a change to PGM 0.4.0 Core. The two bundles author the same four relationship *claims* in different places:

- [`pgm-links/`](pgm-links/) enriches each Markdown Link in place with a YAML Flow Mapping in its ordinary title. These are PGM 0.4.0 Relationship occurrences.
- [`frontmatter-proposal/`](frontmatter-proposal/) illustrates the proposed `relationships:` list from OKF #16 and retains bare body Links for baseline OKF readers. Current OKF 0.2 does not assign relationship semantics to that list. A PGM 0.4.0 processor preserves it as a Concept Property and sees the four body Links as **untyped** Relationships.

Run from the repository root after installing `parser/requirements.txt` with a supported Python version:

```sh
python parser/pgmark.py parse interop/okf-relationship-carriers/pgm-links --format summary
python parser/pgmark.py parse interop/okf-relationship-carriers/frontmatter-proposal --format summary
python -m unittest discover -s tests -p 'test_okf_relationship_carriers.py' -v
```

The test compares the PGM Core Result with an explicitly **optional, experimental OKF projection**. It does not implement or claim conformance to a settled OKF relationship profile.

## What the comparison exposes

| Question | PGM link-authoritative source | Proposed frontmatter-authoritative source |
| --- | --- | --- |
| Where is the assertion authored? | At each Link occurrence. | In a separate frontmatter list; body Links may duplicate the targets. |
| What does PGM Core see? | Four typed `functions/checkout` → `functions/handler` occurrences with complete YAML Properties. | Four untyped body-Link occurrences, plus an uninterpreted `relationships` Node Property. |
| What does `direction: inbound` do? | It is retained as a Property; it does **not** reverse the PGM Core edge. | In the candidate #16 interpretation, it describes an inbound edge relative to the carrying Concept. |
| Can an adapter show `handler` → `checkout`? | Yes, **only** by an explicitly named projection rule for `direction: inbound`; the Core edge remains unchanged. | Yes, if #16 adopts that interpretation. |
| What happens to repeated assertions? | Both equal Link occurrences survive, share a semantic key, and have distinct portable occurrence IDs. | Two list entries are present, but #16 has not defined their occurrence identity or reconciliation with body Links. |
| Can an edge carry arbitrary Properties? | Yes. `confidence: 0.85` remains a Property. | The #16 draft does not define a portable `confidence` field, so this example omits it from that list. |
| What is authoritative if the two carriers disagree? | The Markdown Link is the PGM source. | Open design decision for OKF #16; this exercise does not invent precedence. |

The leading `←` in the example is merely human-facing Markdown text. PGM 0.4.0 derives Core direction from the containing Concept to the Link destination ([§5.2](../../SPEC.md#52-relationship-existence-occurrence-and-direction)). The YAML `direction` Property is valid under [§5.3](../../SPEC.md#53-relationship-properties-from-a-link-title), but only an additional profile may give it effective-direction semantics. Consequently the experimental projection in the test reverses `inbound` for comparison **without altering the PGM Core Result or PGM JSON Exchange**.

## Optional relationship-trust interpretation

PGM [§5.6](../../SPEC.md#56-okf-named-relationship-properties) preserves `generated` and `verified` in a Link title but deliberately does not apply OKF's Concept-specific trust rules to them. A separately named, opt-in *PGM–OKF Relationship Trust Profile* could validate the same event shapes and derive a tier **per occurrence**:

1. No `verified`: `unverified`, even when `generated` is present or the source Concept is human-reviewed.
2. `verified` by one or more non-human actors only: `machine-confirmed`.
3. At least one `human:<id>` verifier: `human-reviewed`.

The fixture covers all three cases and both the single-map and list spellings of `verified`. The test implements only this small, valid-input derivation; it is **not** a complete validator for OKF actors, event histories, or signatures. `confidence` never determines the tier. Declared `by` values and PGM hashes do not authenticate an actor ([PGM §10](../../SPEC.md#10-security-and-resource-considerations)). `refuted` is still an [open OKF proposal](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/13), not a rule adopted here.

Under such a profile, malformed event shapes or missing timezone offsets should fail the **profile interpretation**, not erase a valid PGM Core Relationship. The test demonstrates that boundary. A consumer that reads both the frontmatter list and body Links also needs an explicit reconciliation rule to avoid double-counting; neither PGM 0.4.0 nor the draft #16 supplies that rule.

The complete Property map contributes to PGM's portable Relationship key and occurrence ID ([§6](../../SPEC.md#6-portable-relationship-identification-profile)). Adding `verified` therefore changes those technical IDs; they must not be presented as durable IDs for an evolving business assertion. Whether a verification covers all edge Properties, how copied verification is attributed across bundles, and whether an old verification survives an edit need explicit profile decisions. This exercise does not silently choose them.

## Version boundary

PGM 0.4.0 Public Draft normatively pins the historical OKF 0.2 text at [`3fcbb9f`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md). The active [OKF specification at `ad30107`](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md) still calls itself 0.2 but changes several date-only fields into offset-bearing datetimes; [OKF #24](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/24) tracks that versioning problem. The two example bundles omit those fields and use explicit-offset datetime strings for all trust events, so they avoid this *known* difference. This is a scoped compatibility check, not a claim that the two OKF texts are identical.
