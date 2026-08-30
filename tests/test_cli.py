from pathlib import Path
import tempfile
import unittest

from abi_kgb.cli import main

DATA = Path(__file__).parent / "data"


class CliTests(unittest.TestCase):
    def test_offline_report_and_write(self):
        with tempfile.TemporaryDirectory() as td:
            rc = main([
                str(DATA / "minimal.abi"),
                "--scheduler", "local",
                "--abinit", "/bin/true",
                "--mpi-launcher", "/bin/true",
                "--autoparal-log", str(DATA / "autoparal_local.log"),
                "--max-cpus", "20",
                "--npfft-max", "1",
                "--write", "--write-dir", td,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "minimal.kgb.abi").exists())
            self.assertTrue((Path(td) / "run_kgb.sh").exists())


if __name__ == "__main__":
    unittest.main()
