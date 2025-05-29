"""
Pydantic Task Documents for DMAx jobs.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any

class DmaxStructureTaskDocument(BaseModel):
    """
    Task document for polymer structure generation.
    """
    packmol_pdb: Optional[str] = Field(
        None, description="Contents of the packmol PDB file"
    )
    polymer_pdb: Optional[str] = Field(
        None, description="Contents of the generated polymer PDB file"
    )
    builder_wrapper: Optional[Any] = Field(
        None, description="Serialized PSPBuilderWrapper for reuse"
    )

class DmaxForceFieldTaskDocument(BaseModel):
    """
    Task document for forcefield parametrization.
    """
    data_file: str = Field(
        ..., description="Path or name of the generated LAMMPS data file"
    )
    lammps_data: Optional[str] = Field(
        None, description="Contents of the generated LAMMPS data file"
    )
    forcefield_type: str = Field(
        ..., description="Type of forcefield used ('opls' or 'gaff2')"
    )

class DmaxDataGenerationFlowDocument(BaseModel):
    """
    Document for the complete DMAx data generation flow.
    """
    packmol_pdb: Optional[Any] = Field(
        None, description="Reference or contents of the packmol PDB file"
    )
    polymer_pdb: Optional[Any] = Field(
        None, description="Reference or contents of the generated polymer PDB file"
    )
    lammps_data: Optional[Any] = Field(
        None, description="Reference or contents of the generated LAMMPS data file"
    )

class DmaxLammpsInputDocument(BaseModel):
    """
    Task document for generated LAMMPS input files.
    """
    input_dir: str = Field(
        ..., description="Directory containing generated LAMMPS input and slurm files"
    )
    data_file: str = Field(
        ..., description="Filename of the LAMMPS data file in the input directory"
    )
    input_file: str = Field(
        ..., description="Filename of the LAMMPS input script generated from template"
    )
    slurm_file: str = Field(
        ..., description="Filename of the SLURM run script in the input directory"
    )

class DmaxLammpsRunDocument(BaseModel):
    """
    Task document for a submitted LAMMPS SLURM run.
    """
    job_id: str = Field(
        ..., description="SLURM job ID for the LAMMPS run"
    )
    job_status: Optional[str] = Field(
        None, description="Current status of the SLURM job"
    )
    output_file: Optional[str] = Field(
        None, description="Path to the output file of the LAMMPS run"
    )
    error_file: Optional[str] = Field(
        None, description="Path to the error file of the LAMMPS run"
    )
    submission_time: Optional[str] = Field(
        None, description="Time when the job was submitted"
    )
    start_time: Optional[str] = Field(
        None, description="Time when the job started running"
    )
    end_time: Optional[str] = Field(
        None, description="Time when the job finished"
    )
    walltime: Optional[str] = Field(
        None, description="Total wall time used by the job"
    )
    nodes: Optional[int] = Field(
        None, description="Number of nodes allocated for the job"
    )
    ppn: Optional[int] = Field(
        None, description="Number of processors per node"
    )
    memory: Optional[str] = Field(
        None, description="Memory allocated for the job"
    )
    partition: Optional[str] = Field(
        None, description="SLURM partition where the job is submitted"
    )
    account: Optional[str] = Field(
        None, description="Account used for job submission"
    )
    job_name: Optional[str] = Field(
        None, description="Name of the job as submitted to SLURM"
    )
    exit_code: Optional[int] = Field(
        None, description="Exit code of the job"
    )
    lammps_input: Optional[str] = Field(
        None, description="Contents of the LAMMPS input script"
    )
    lammps_data: Optional[str] = Field(
        None, description="Contents of the LAMMPS data file"
    )
    packmol_pdb: Optional[str] = Field(
        None, description="Contents of the packmol PDB file"
    )
    polymer_pdb: Optional[str] = Field(
        None, description="Contents of the generated polymer PDB file"
    )
