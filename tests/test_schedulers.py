import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from abi_kgb.models import SystemInfo
from abi_kgb.schedulers.local import LocalBackend
from abi_kgb.schedulers.pbs import PbsBackend
from abi_kgb.schedulers.slurm import SlurmBackend


def system():
    return SystemInfo("h", "Linux", "k", False, "cpu", 40, 20, 1, 2, 1, 64, 60, 64)


class SchedulerTests(unittest.TestCase):
    def test_local_defaults_physical(self):
        r = LocalBackend().resources(system())
        self.assertEqual(r.max_total_ranks, 20)
        self.assertEqual(r.memory_per_node_gib, 60)

    def test_slurm_active(self):
        env = {
            "SLURM_JOB_ID": "42", "SLURM_NNODES": "2", "SLURM_NTASKS": "112",
            "SLURM_CPUS_ON_NODE": "56", "SLURM_MEM_PER_NODE": "256000",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            r = SlurmBackend().resources(system())
            self.assertEqual((r.nodes, r.max_total_ranks, r.max_ranks_per_node), (2, 112, 56))
            self.assertAlmostEqual(r.memory_per_node_gib, 250.0)

    def test_pbs_nodefile(self):
        with tempfile.TemporaryDirectory() as td:
            nf = Path(td) / "nodes"
            nf.write_text("n1\n" * 4 + "n2\n" * 4)
            env = {"PBS_JOBID": "1.server", "PBS_NODEFILE": str(nf), "PBS_O_WORKDIR": td}
            with mock.patch.dict(os.environ, env, clear=True):
                r = PbsBackend().resources(system(), memory_per_node=32)
                self.assertEqual((r.nodes, r.max_total_ranks, r.max_ranks_per_node), (2, 8, 4))


if __name__ == "__main__":
    unittest.main()
