"""
Flow for Dynamic Mechanical Analysis (DMA) simulations.

Chains structure generation and forcefield parametrization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from jobflow import Flow, Maker  # ensure Flow is imported

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
from atomate2.dmax.schemas.task import DmaxDataGenerationFlowDocument


@dataclass
class BaseDataGenerationFlow(Maker):
    name: str = "DMA workflow"
    smiles: str = "[*]CC[*]"
    left_cap: str = "C"
    right_cap: str = "C"
    length: int = 10
    num_molecules: int = 5
    density: float = 0.8
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False

    def make(self) -> Flow:
        # determine working directory
        wd = str(self.out_dir) if self.out_dir else None
        # structure generation
        struct_job = PSPStructureMaker(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=wd,
            num_conf=self.num_conf,
            loop=self.loop,
            return_builder=True,
        ).make()
        # forcefield
        ff_job = ForceFieldMaker(out_dir=wd).make(struct_job.output)
        # assemble final document using task documents from each job
        struct_doc = struct_job.output  # DmaxStructureTaskDocument
        ff_doc = ff_job.output  # DmaxForceFieldTaskDocument
        doc = DmaxDataGenerationFlowDocument(
            packmol_pdb=struct_doc.packmol_pdb,
            polymer_pdb=struct_doc.polymer_pdb,
            lammps_data=ff_doc.lammps_data,
        )
        # return a Flow chaining the structure and forcefield jobs
        return Flow([struct_job, ff_job], doc, name=self.name)


@dataclass
class StructureEquilibrationFlow(Maker):
    """
    Full flow: build structure, parametrize forcefield, generate LAMMPS input for structure equilibration,
    run the simulation, and parse the results.
    """
    # inherit or re-specify relevant parameters
    smiles: str = "[*]CC[*]"
    left_cap: str = "C"
    right_cap: str = "C"
    length: int = 10
    num_molecules: int = 5
    density: float = 0.8
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False

    def make(self) -> Flow:
        # Base data-generation
        wd = str(self.out_dir) if self.out_dir else None
        struct_job = PSPStructureMaker(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=wd,
            num_conf=self.num_conf,
            loop=self.loop,
            return_builder=True,
        ).make()
        ff_job = ForceFieldMaker(out_dir=wd).make(struct_job.output)

        # Generate LAMMPS input for structure equilibration
        from atomate2.dmax.jobs.lammps_input_generation import StructureEquilInputMaker
        input_job = StructureEquilInputMaker(
            name='structure_equilibration',
            data_file_type=ff_job.output.forcefield_type,
            out_dir=wd
        ).make(ff_job.output.data_file)

        # Placeholder: run the LAMMPS simulation
        # sim_job = YourRunMaker(...).make(input_job.output.input_dir)

        # Placeholder: parse the LAMMPS output
        # parse_job = YourParseMaker(...).make(sim_job.output)

        # return flow (for now, output the input doc)
        return Flow([
            struct_job,
            ff_job,
            input_job,
            # sim_job,
            # parse_job
        ],
        input_job.output,
        name='structure_equilibration_flow')
