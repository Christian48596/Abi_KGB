from pathlib import Path
import tempfile
import unittest

from abi_kgb.models import Candidate, LauncherPlan, SchedulerInfo
from abi_kgb.writers.scripts import write_run_script


class WriterTests(unittest.TestCase):
    def test_slurm_writer(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.slurm"
            write_run_script(
                path, input_path=Path("calc.kgb.abi"), candidate=Candidate(28,1,4,1,112,1),
                scheduler=SchedulerInfo("slurm", False), launcher=LauncherPlan("mpiexec", "mpiexec -np {ranks}", "x"),
                nodes=2, ranks_per_node=56, abinit="abinit", partition="cpu", walltime="12:00:00"
            )
            text = path.read_text()
            self.assertIn("#SBATCH --ntasks=112", text)
            self.assertIn("#SBATCH --ntasks-per-node=56", text)
            self.assertIn("mpiexec -np 112", text)

    def test_pbs_writer(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.pbs"
            write_run_script(
                path, input_path=Path("calc.kgb.abi"), candidate=Candidate(4,1,5,1,20,1),
                scheduler=SchedulerInfo("pbs", False, flavor="openpbs"), launcher=LauncherPlan("mpiexec", "mpiexec -np {ranks}", "x"),
                nodes=1, ranks_per_node=20, abinit="abinit", queue="workq", pbs_flavor="openpbs"
            )
            text = path.read_text()
            self.assertIn("#PBS -l select=1:ncpus=20:mpiprocs=20", text)
            self.assertIn("q", text)


if __name__ == "__main__":
    unittest.main()
