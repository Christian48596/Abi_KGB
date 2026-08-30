from pathlib import Path
import unittest

from abi_kgb.abinit.autoparal import parse_autoparal_text

DATA = Path(__file__).parent / "data"


class AutoparalTests(unittest.TestCase):
    def test_real_shape(self):
        rows = parse_autoparal_text((DATA / "autoparal_112.log").read_text())
        self.assertEqual(rows[0].mpi, 112)
        self.assertEqual((rows[0].np_spkpt, rows[0].npfft, rows[0].npband), (28, 2, 2))
        self.assertGreater(rows[0].weight, rows[-1].weight)

    def test_infers_npspinor_from_mpi_product(self):
        text = "| 1| 1| 4| 2| 8| 10.0|"
        row = parse_autoparal_text(text)[0]
        self.assertEqual(row.npspinor, 2)


if __name__ == "__main__":
    unittest.main()
