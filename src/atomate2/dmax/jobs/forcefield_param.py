"""
Job maker for polymer forcefield parametrization via LigParGen or Foyer.
"""
from dataclasses import dataclass, field
from pathlib import Path
from jobflow import Maker, job
import os
import shutil
import importlib

from atomate2.dmax.generators.forcefield import (
    parametrize_auto,
    parametrize_foyer,
    parametrize_ligpargen,
    parametrize_gaff2_pysimm,
    parametrize_gaff2_antechamber,
)
from atomate2.dmax.generators.polymer_structure import PSPBuilderWrapper
from atomate2.dmax.schemas.task import DmaxForceFieldTaskDocument, DmaxStructureTaskDocument

@dataclass
class ForceFieldMaker(Maker):
    """
    Maker to parametrize polymer structures with flexible forcefield selection.

    Parameters
    ----------
    forcefield : str
        Which forcefield to generate: 'opls', 'gaff2', or 'auto' (try all in order).
    generator : str
        Which generator to use: 'psp', 'foyer', 'pysimm', 'antechamber', or 'auto'
        (follow hierarchy based on forcefield).
    out_dir : str | None
        Optional directory for intermediate outputs (not commonly used).

    When `forcefield='auto'` and `generator='auto'`, will attempt:
    LigParGen OPLS → Foyer OPLS → GAFF2 via pysimm → GAFF2 via antechamber.
    Users can restrict to a specific forcefield or generator.
    """
    name: str = "forcefield_parametrization"
    # Choose which forcefield to apply: 'opls', 'gaff2', or 'auto' (fallback)
    forcefield: str = "auto"
    # Choose generator: 'psp', 'foyer', 'pysimm', 'antechamber', or 'auto'
    generator: str = "auto"
    out_dir: str | None = None

    @job(output_schema=DmaxForceFieldTaskDocument)
    def make(self, amor) -> DmaxForceFieldTaskDocument:
        # handle structure document inputs
        if isinstance(amor, DmaxStructureTaskDocument):
            # reconstruct PSPBuilderWrapper and ensure builder has cell dims
            if amor.builder_wrapper:
                wrapper = PSPBuilderWrapper.from_dict(amor.builder_wrapper)
                # get actual PSPBuilder instance
                builder = wrapper.get_builder()
                # only call Build if cell bounds not set
                try:
                    # builder.cell is set after Build; check attribute
                    getattr(builder, 'cell')
                except Exception:
                    builder.Build()
                wrapper._builder = builder
                amor = wrapper
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
        # select parametrization function based on user request
        # fallback auto uses parametrize_auto
        def run_auto():
            return parametrize_auto(amor)
        # mapping generator strings to functions
        gen_funcs = {
            'psp': parametrize_ligpargen,
            'foyer': parametrize_foyer,
            'pysimm': parametrize_gaff2_pysimm,
            'antechamber': parametrize_gaff2_antechamber,
        }
        # determine which forcefield(s) and generator to try
        data_path = None
        if self.forcefield != 'auto':
            # user-specified forcefield
            if self.forcefield == 'opls':
                gens = [self.generator] if self.generator != 'auto' else ['psp', 'foyer']
            else:  # gaff2
                gens = [self.generator] if self.generator != 'auto' else ['pysimm', 'antechamber']
            for g in gens:
                try:
                    func = gen_funcs[g]
                    data_path = func(amor)
                    break
                except Exception:
                    continue
            if data_path is None:
                raise RuntimeError(f"Failed to parametrize {self.forcefield} with {gens}")
        else:
            # auto forcefield detection
            if self.generator != 'auto':
                # user asked specific generator under auto type, dispatch
                func = gen_funcs[self.generator]
                data_path = func(amor)
            else:
                data_path = parametrize_auto(amor)
        # move data into job cwd
        if not os.path.isabs(data_path) or not os.path.exists(data_path):
            data_path = os.path.join(os.getcwd(), os.path.basename(data_path))
        else:
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
        std_name = f"{name_no_ext}.data"
        std_path = os.path.join(os.getcwd(), std_name)
        shutil.move(data_path, std_path)
        # read file contents after rename
        with open(std_path, 'r') as f:
            data_txt = f.read()
        # return absolute path so next maker can locate and copy it
        return DmaxForceFieldTaskDocument(
            data_file=std_path,
            lammps_data=data_txt,
            forcefield_type=ftype,
        )
