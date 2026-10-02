# Releasing a PGM Public Draft

The PGM 0.4.2 Relationship Trust Profile publication uses tags of the form
`v0.4.2-public-draft.N`. Draft sequence `N` maps to PEP 440 Python package
version `0.4.2aN`. This release adds the optional
[Relationship Trust Profile](profiles/relationship-trust/SPEC.md) while PGM Core,
PGM JSON Exchange v1, and the independent PGM Schema keep their 0.4.0 Public
Draft semantics. The withdrawn `v0.4.1-public-draft.1` tag MUST NOT be moved or
reused.

## 1. Prepare the candidate

Work from the intended release commit and require a clean tree:

```sh
git status --short --branch
git diff --check
```

Confirm that `SPEC.md` and PGM Schema still identify their unchanged 0.4.0
Public Drafts, while the profile, `pyproject.toml`, parser, release workflow,
and changelog identify the 0.4.2 profile release. Verify the tag-to-package
mapping (`public-draft.N` to Python `0.4.2aN`) and the independent PGM Schema
version `0.4.0-public-draft.1`. Replace the release-candidate label in
`CHANGELOG.md` with the actual publication date only on the reviewed release
commit.

Every third-party GitHub Action in the workflows is pinned to an immutable
commit SHA reviewed for this draft. Re-resolve each upstream release tag and
review its changes before updating one of those SHAs.

## 2. Reproduce the release checks

Create an isolated Python environment, then run:

```sh
python -m pip install --constraint parser/constraints.txt --editable .
python -m unittest discover -s tests -v
pgmark validate demo/bundle
pgmark validate demo-vault
pgmark trust interop/okf-relationship-carriers/pgm-links --json
pgmark parse demo/bundle --format json > actual.graph.json
diff -u demo/expected.graph.json actual.graph.json
pgmark import-json demo/expected.graph.json --format json > reexported.graph.json
diff -u demo/expected.graph.json reexported.graph.json
pgmark import-json demo/expected.graph.json --format cypher > imported.cypher
diff -u demo/expected.cypher imported.cypher
pgmark parse demo/bundle --format cypher > actual.cypher
diff -u demo/expected.cypher actual.cypher
pgmark parse demo/bundle --format cypher --relationship-mode merge > actual-merge.cypher
diff -u demo/expected-merge.cypher actual-merge.cypher
```

Validate the separate PGM Schema profile:

```sh
cd pgm-schema
NO_UPDATE_NOTIFIER=1 PYTHON=python npm test
NO_UPDATE_NOTIFIER=1 PYTHON=python npm run validate
cd ..
NO_UPDATE_NOTIFIER=1 PYTHON=python node pgm-schema/validate.mjs demo-vault-schema demo-vault
```

Return to the repository root and build the Python artifacts:

```sh
python -m pip install --constraint parser/constraints.txt build==1.2.2.post1
python -m build
```

CI repeats these checks on Python 3.10 through 3.14 and Node.js 20, 22, and 24.
A release candidate is ready only after every required check succeeds on the
exact commit to be tagged.

Smoke-test the built wheel, rather than the source tree, in a fresh environment:

```sh
PGM_WHEEL_ENV="$(mktemp -d)/venv"
python -m venv "$PGM_WHEEL_ENV"
"$PGM_WHEEL_ENV/bin/python" -m pip install --constraint parser/constraints.txt dist/*.whl
"$PGM_WHEEL_ENV/bin/python" -m pip check
"$PGM_WHEEL_ENV/bin/pgmark" --version
"$PGM_WHEEL_ENV/bin/pgmark" validate demo/bundle
"$PGM_WHEEL_ENV/bin/pgmark" validate demo-vault
"$PGM_WHEEL_ENV/bin/pgmark" trust interop/okf-relationship-carriers/pgm-links --json
"$PGM_WHEEL_ENV/bin/pgmark" parse demo/bundle --format json > wheel.graph.json
diff -u demo/expected.graph.json wheel.graph.json
"$PGM_WHEEL_ENV/bin/pgmark" import-json demo/expected.graph.json --format json > wheel-reexported.graph.json
diff -u demo/expected.graph.json wheel-reexported.graph.json
"$PGM_WHEEL_ENV/bin/pgmark" import-json demo/expected.graph.json --format cypher > wheel-imported.cypher
diff -u demo/expected.cypher wheel-imported.cypher
"$PGM_WHEEL_ENV/bin/pgmark" parse demo/bundle --format cypher > wheel.cypher
diff -u demo/expected.cypher wheel.cypher
"$PGM_WHEEL_ENV/bin/pgmark" parse demo/bundle --format cypher --relationship-mode merge > wheel-merge.cypher
diff -u demo/expected-merge.cypher wheel-merge.cypher
```

## 3. Tag the reviewed commit

Choose the next draft sequence number, update the Python package and `pgmark`
processor to the corresponding `0.4.2aN` version, keep PGM Schema at its
independent `0.4.0-public-draft.1`, then create an annotated tag. For Draft 1:

```sh
git tag -a v0.4.2-public-draft.1 -m "PGM 0.4.2 Relationship Trust Profile Public Draft 1"
git push origin v0.4.2-public-draft.1
```

Pushing a matching tag triggers `.github/workflows/release.yml`. The workflow
reruns the checks, builds the wheel, source distribution, public-draft source
bundle and checksums, then creates a draft GitHub Release.

## 4. Publish deliberately

Before publishing the generated GitHub Release:

1. verify that the tag resolves to the reviewed commit;
2. download and verify `SHA256SUMS`;
3. confirm that the fresh-wheel smoke test reproduced the JSON exchange and
   Cypher snapshots;
4. inspect the rendered specification and changelog;
5. inspect the standalone Ada Demo Vault ZIP and confirm that it contains 47
   Markdown files, `ATTRIBUTION.txt`, and no `.obsidian` directory;
6. confirm that the release is clearly labelled **Public Draft**; and
7. confirm the release description distinguishes the optional Trust Profile
   from unchanged PGM Core and PGM Schema; and
8. publish the draft Release manually.

Do not reuse or move an already published tag. Corrections receive the next
`public-draft.N` tag.
