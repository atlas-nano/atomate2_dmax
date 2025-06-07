import os
from dataclasses import dataclass
from pathlib import Path

from jobflow import Maker, job, Response

from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
from atomate2.lammps.run import run_lammps
from atomate2 import SETTINGS

@dataclass
class LammpsRunMaker(Maker):
    """Run a single LAMMPS job with custodian-like robustness."""

    name: str = "lammps_run"
    # runtime options (mirrors SETTINGS defaults)
    lmp_cmd: str = SETTINGS.LAMMPS_CMD
    lmp_mpi_cmd: str = SETTINGS.LAMMPS_MPICMD
    lmp_suffix: list[str] | str | None = None
    lmp_packages: list[str] | str | None = None
    lmp_flags: list[str] | str | None = None
    stdout_file: str = "stdout.log"
    stderr_file: str = "stderr.log"

    @job(output_schema=DmaxLammpsRunDocument)
    def make(self, input_doc: DmaxLammpsInputDocument):
        # change into calc directory, run, return restart + (pseudo) job-id
        pwd = Path.cwd()
        try:
            os.chdir(Path(input_doc.input_dir))
            run_lammps(                                   
                lammps_input_file=input_doc.input_file,
                lammps_cmd=self.lmp_cmd,
                lammps_mpi_cmd=self.lmp_mpi_cmd,
                lammps_suffix=self.lmp_suffix,
                lammps_pks=self.lmp_packages,
                lammps_run_flags=self.lmp_flags,
                stdout_file=self.stdout_file,
                stderr_file=self.stderr_file,
            )
        finally:
            os.chdir(pwd)
        restart = Path(input_doc.input_dir, "restart.equil")
        # FireWorks / jobflow-remote will insert the real SLURM/PBS id at launch time,
        # so here we just label it “pending”.
        return Response(output=DmaxLammpsRunDocument(job_id="pending", restart_file=str(restart)))