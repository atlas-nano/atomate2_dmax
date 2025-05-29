"""
Job maker for polymer forcefield parametrization via LigParGen or Foyer.
"""
from dataclasses import dataclass, field
from pathlib import Path
from jobflow import Maker, job
import os
import shutil
import importlib

from atomate2.dmax.generators.forcefield import parametrize_auto, parametrize_foyer
from atomate2.dmax.generators.polymer_structure import PSPBuilderWrapper
from atomate2.dmax.schemas.task import DmaxForceFieldTaskDocument, DmaxStructureTaskDocument

@dataclass
class ForceFieldMaker(Maker):
    """
    Maker to parametrize polymer structures.

    Attributes
    ----------
    amor : PSPBuilder instance
        PSPBuilder instance needed for forcefield parametrization.
    method : str
        'ligpargen' or 'foyer'.
    forcefield_name : str | None
        Name of the forcefield for foyer.
    """
    name: str = "forcefield_parametrization"
    method: str = field(default="auto")
    out_dir: str | None = None

    @job(output_schema=DmaxForceFieldTaskDocument)
    def make(self, amor) -> DmaxForceFieldTaskDocument:
        # handle structure document inputs
        if isinstance(amor, DmaxStructureTaskDocument):
            # use builder_wrapper if available to reuse PSPBuilder without rebuild
            if amor.builder_wrapper:
                amor = PSPBuilderWrapper.from_dict(amor.builder_wrapper)
            else:
                # fallback: write PDB text to file for foyer
                pdb_txt = amor.polymer_pdb or amor.packmol_pdb
                if not pdb_txt:
                    raise ValueError("Structure document missing PDB content")
                pdb_path = os.path.join(os.getcwd(), "structure.pdb")
                with open(pdb_path, 'w') as f:
                    f.write(pdb_txt)
                amor = pdb_path
        """
        Generate LAMMPS data file from PSP builder `amor` or its wrapper.
        By default uses automatic selection.
        """
        # determine the data file path via appropriate generator
        if isinstance(amor, str) and amor.lower().endswith('.pdb'):
            data_path = parametrize_foyer(amor)
        else:
            if isinstance(amor, dict):
                amor = PSPBuilderWrapper.from_dict(amor)
            if not hasattr(amor, 'get_builder'):
                raise ValueError('Input must be a PSPBuilderWrapper or .pdb path')
            # full auto parametrization
            orig_dir = amor.out_dir
            amor.out_dir = orig_dir
            data_path = parametrize_auto(amor)
            # move into job cwd
            dest = os.path.join(os.getcwd(), os.path.basename(data_path))
            shutil.move(data_path, dest)
            data_path = dest
        # read file contents
        with open(data_path, 'r') as f:
            data_txt = f.read()
        # determine forcefield type from filename
        fname = os.path.basename(data_path).lower()
        if 'opls' in fname:
            ftype = 'opls'
        else:
            ftype = 'gaff2'
        # rename to standardized 'data.<basename>' (no extension)
        base = os.path.basename(data_path)
        name_no_ext, _ = os.path.splitext(base)
        std_name = f"data.{name_no_ext}"
        std_path = os.path.join(os.getcwd(), std_name)
        shutil.move(data_path, std_path)
        # read file contents after rename
        with open(std_path, 'r') as f:
            data_txt = f.read()
        # return absolute path so next maker can locate and copy it
        return DmaxForceFieldTaskDocument(
            data_file=std_path,
            lammps_data=data_txt,
            forcefield_type=ftype
        )
