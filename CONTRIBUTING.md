# Contributing to Abi_KGB

Contributions are welcome through GitHub issues and pull requests.

## Development setup

```bash
git clone https://github.com/Christian48596/Abi_KGB.git
cd Abi_KGB
python3 -m pip install -e .
python3 run_tests.py
```

Abi_KGB deliberately has no runtime third-party Python dependencies. Please preserve that property unless a dependency provides a clear portability or correctness benefit that cannot reasonably be implemented with the standard library.

## Pull requests

A pull request should:

1. explain the scheduler/MPI/ABINIT behavior being changed,
2. include or update tests,
3. update user-facing documentation where behavior changes,
4. avoid including private cluster hostnames, usernames, home paths, queue policies, credentials, or proprietary input files, and
5. keep unsupported cases explicit rather than silently guessing.

For scheduler or MPI support, include sanitized command output demonstrating the environment, e.g. `mpiexec --version`, scheduler environment keys, and generated script output.

## Reporting bugs

Please include:

- Abi_KGB version,
- ABINIT version,
- MPI implementation/version,
- scheduler and flavor,
- sanitized `abi-kgb doctor` output,
- the smallest ABINIT input that reproduces the issue, if shareable,
- the Abi_KGB command used, and
- the exact error/warning.

Do not post credentials or private job/account identifiers.

## Scientific correctness

Changes to KGB legality or ranking should be checked against ABINIT documentation and, where possible, a real `autoparal` output. Abi_KGB intentionally treats ABINIT's own autoparal table as authoritative for legal runtime layouts.
