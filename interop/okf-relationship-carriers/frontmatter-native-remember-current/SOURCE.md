# remember: current-key frontmatter-native input

This is a separate, verbatim two-file extract of Andrew Crenshaw's public [CC0-licensed sample bundle](https://github.com/andrewcrenshaw/remember-okf-sample-bundle/blob/500ff25d6f79ea0160771b3f4cda5762dee08ed6/LICENSE) at commit [`500ff25d6f79ea0160771b3f4cda5762dee08ed6`](https://github.com/andrewcrenshaw/remember-okf-sample-bundle/tree/500ff25d6f79ea0160771b3f4cda5762dee08ed6). It does **not** replace the earlier [`3806111` deprecated-input extract](../frontmatter-native-remember/SOURCE.md) or represent a complete bundle.

| Copied file | Upstream source | SHA-256 |
| --- | --- | --- |
| [`bundle/facts/okf-v0-2-conformance-fixture-lesson-e-001.md`](bundle/facts/okf-v0-2-conformance-fixture-lesson-e-001.md) | [concept](https://github.com/andrewcrenshaw/remember-okf-sample-bundle/blob/500ff25d6f79ea0160771b3f4cda5762dee08ed6/bundle/facts/okf-v0-2-conformance-fixture-lesson-e-001.md) | `124116df0e3745101bf0c630366fd58d73ac4b107ff1a66e86b2f5d0b55acc0c` |
| [`bundle/log.md`](bundle/log.md) | [bundle-root log](https://github.com/andrewcrenshaw/remember-okf-sample-bundle/blob/500ff25d6f79ea0160771b3f4cda5762dee08ed6/bundle/log.md) | `a1f0a09c00e3c8f8cba7677925ae7a7318051c6128b3f4acb7e599f235e88883` |

The exporter stores `contradicts` here; the old pin stores deprecated `contested_by`. Both inputs are **frontmatter-native**, and neither contains a PGM Link assertion. The newer root log affirms the exact `supersedes` pair with a human actor, but its predecessor target is absent from this extract *and* the upstream manifest's present entries. Consequently, the informative #22 view records a readable affirmation but excludes nothing.

This producer's [pinned manifest](https://github.com/andrewcrenshaw/remember-okf-sample-bundle/blob/500ff25d6f79ea0160771b3f4cda5762dee08ed6/bundle/.manifest.json) explicitly declares `identifiers.form: "remember://lesson/<id>"`. The query exercise applies **that producer-specific template** to the concept's bare `id` and frontmatter target values before comparing them to the log's stable IDs. This is not a generic rule for OKF or PGM identifiers. The unmodified source files remain authoritative for this extract; the normalized query rows are derived views.
