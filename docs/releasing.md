# Releasing Abi_KGB

1. Ensure `main` CI is green.
2. Update `CHANGELOG.md`.
3. Update the version in `src/abi_kgb/__init__.py`, `pyproject.toml`, and `CITATION.cff`.
4. Run:

```bash
python3 run_tests.py
python3 -m compileall -q src/abi_kgb
```

5. Create a signed or annotated git tag, e.g. `v1.0.0`.
6. Create a GitHub release from that tag.
7. Archive the release in Zenodo (or another long-term research-software archive) and add the DOI to `CITATION.cff`.
