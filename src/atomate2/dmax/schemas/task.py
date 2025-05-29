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
