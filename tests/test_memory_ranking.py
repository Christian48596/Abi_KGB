from pathlib import Path
import unittest

from abi_kgb.abinit.autoparal import parse_autoparal_text
from abi_kgb.models import Calibration, ResourceEnvelope, SystemInfo
from abi_kgb.optimization.ranking import rank_candidates

DATA = Path(__file__).parent / "data"


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.system = SystemInfo(
            hostname="test", os_name="Linux", kernel="x", is_wsl=True,
            cpu_model="CPU", logical_cpus=40, physical_cores=20, sockets=1,
            threads_per_core=2, numa_nodes=1, mem_total_gib=31.0,
            mem_available_gib=30.0, mem_effective_limit_gib=31.0,
        )

    def test_calibrated_local(self):
        candidates = parse_autoparal_text((DATA / "autoparal_local.log").read_text())
        resources = ResourceEnvelope(1, 20, 20, 31.0, "test", 20, 40)
        ranked = rank_candidates(
            candidates, system=self.system, resources=resources, reserve_fraction=0.2,
            npfft_max=1, calibrations=[Calibration(7, 8.0), Calibration(20, 14.0)]
        )
        self.assertEqual(ranked[0].candidate.mpi, 20)
        self.assertEqual(ranked[0].memory_status, "OK")

    def test_reject_oom(self):
        candidates = parse_autoparal_text((DATA / "autoparal_local.log").read_text())
        resources = ResourceEnvelope(1, 20, 20, 16.0, "test", 20, 40)
        ranked = rank_candidates(
            candidates, system=self.system, resources=resources, reserve_fraction=0.2,
            npfft_max=1, calibrations=[Calibration(20, 20.0)]
        )
        r20 = next(r for r in ranked if r.candidate.mpi == 20)
        self.assertEqual(r20.memory_status, "REJECT")


if __name__ == "__main__":
    unittest.main()
