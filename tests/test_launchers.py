import unittest

from abi_kgb.launchers import select_launcher
from abi_kgb.models import MpiInfo, SchedulerInfo


class LauncherTests(unittest.TestCase):
    def test_mpich_slurm_hydra(self):
        mpi = MpiInfo("/x/mpiexec", "mpiexec", "mpich", "MPICH", ("ssh", "slurm"), ())
        sched = SchedulerInfo("slurm", True)
        p = select_launcher(mpi, sched)
        self.assertIn("mpiexec", p.command_template)
        self.assertNotIn("srun", p.command_template)

    def test_mpich_pbs(self):
        mpi = MpiInfo("/x/mpiexec", "mpiexec", "mpich", "MPICH", ("ssh", "pbs"), ())
        sched = SchedulerInfo("pbs", True, flavor="openpbs", nodefile="/tmp/nodes")
        p = select_launcher(mpi, sched)
        self.assertIn("-launcher pbs", p.command_template)

    def test_cray_slurm(self):
        mpi = MpiInfo("/x/mpiexec", "mpiexec", "cray-mpich", "Cray", (), ())
        sched = SchedulerInfo("slurm", True)
        self.assertTrue(select_launcher(mpi, sched).command_template.startswith("srun"))


if __name__ == "__main__":
    unittest.main()
