"""
Job maker for polymer structure generation using PSP AmorphousBuilder.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from jobflow import Maker, job

from atomate2.dmax.generators.polymer_structure import build_amorphous_structure
from atomate2.dmax.schemas.task import DmaxStructureTaskDocument


@dataclass
class PSPStructureMaker(Maker):
    """
    Maker to generate amorphous polymer structures from SMILES via PSP.

    Attributes
    ----------
    smiles : str
        SMILES of the repeating polymer unit with attachment points.
    left_cap : str
        SMILES of the left cap group with attachment point.
    right_cap : str
        SMILES of the right cap group with attachment point.
    length : int
        Number of monomers per chain.
    num_molecules : int
        Number of polymer chains in the box.
    density : float
        Initial packing density for the builder (g/cm3).
    box_type : str
        Box type code for PSP (e.g., 'c' for cubic).
    out_dir : Path
        Output directory for the generated structure.
    num_conf : int = 0
        Number of conformers to generate.
    loop : bool = False
        Whether to loop until target density is reached.
    return_builder : bool = False
        Whether to return the builder wrapper or the packmol pdb path.
    """

    name: str = "psp_structure_generation"
    smiles: str = field(default="[*]")
    left_cap: str = field(default="[*]")
    right_cap: str = field(default="[*]")
    length: int = 1
    num_molecules: int = 1
    density: float = 0.1
    box_type: str = "c"
    out_dir: Path = field(default_factory=Path)
    num_conf: int = 1
    loop: bool = False
    return_builder: bool = False

    @job(output_schema=DmaxStructureTaskDocument)
    def make(self) -> DmaxStructureTaskDocument:
        """
        Build the amorphous structure and return either the wrapper (if return_builder)
        or the path to the packmol pdb file.
        """
        # write all structure outputs into the job's own working directory
        outdir = os.getcwd()
        amor = build_amorphous_structure(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=outdir,
            num_conf=self.num_conf,
            loop=self.loop,
        )
        # read packmol and polymer pdb contents
        packmol_pdb = os.path.join(outdir, "packmol", "packmol.pdb")
        mol_dir = os.path.join(outdir, "molecules")
        # assume single PDB in molecules
        mol_files = [f for f in os.listdir(mol_dir) if f.endswith(".pdb")]
        mol_pdb = os.path.join(mol_dir, mol_files[0]) if mol_files else None
        packmol_txt = open(packmol_pdb).read() if os.path.exists(packmol_pdb) else None
        mol_txt = open(mol_pdb).read() if mol_pdb and os.path.exists(mol_pdb) else None
        # return Pydantic document for DB storage
        # include builder wrapper instance if requested, else exclude or serialize minimal dict
        if self.return_builder:
            builder_wrapper = amor
        else:
            builder_wrapper = amor.as_dict()
        return DmaxStructureTaskDocument(
            packmol_pdb=packmol_txt,
            polymer_pdb=mol_txt,
            builder_wrapper=builder_wrapper,
        )
