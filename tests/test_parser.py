from pathlib import Path
import unittest

from abi_kgb.abinit.parser import parse_abi, patch_kgb_block
from abi_kgb.models import Candidate

DATA = Path(__file__).parent / "data"


class ParserTests(unittest.TestCase):
    def test_parse_minimal(self):
        x = parse_abi(DATA / "minimal.abi")
        self.assertEqual(x.nband, 240)
        self.assertEqual(x.spin_k, 28)
        self.assertEqual(x.optdriver, 0)
        self.assertTrue(x.likely_paw)

    def test_patch(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "x.abi"
            patch_kgb_block(DATA / "minimal.abi", out, Candidate(4, 1, 5, 1, 20, 1.0))
            text = out.read_text()
            self.assertIn("paral_kgb 1", text)
            self.assertIn("np_spkpt 4", text)
            self.assertIn("npband 5", text)
            self.assertIn("npfft 1", text)

    def test_patch_spinor_factor(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "x.abi"
            patch_kgb_block(DATA / "minimal.abi", out, Candidate(1, 1, 4, 2, 8, 1.0, npspinor=2))
            self.assertIn("npspinor 2", out.read_text())


if __name__ == "__main__":
    unittest.main()
