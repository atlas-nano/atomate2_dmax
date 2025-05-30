"""
Flow for Dynamic Mechanical Analysis (DMA) simulations.

Chains structure generation and forcefield parametrization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from jobflow import Flow, Maker, Response  # include Response for DMA flow

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
from atomate2.dmax.jobs.lammps_slurm_run import LammpsSlurmRunMaker, LammpsLocalRunMaker
from atomate2.dmax.jobs.structure_equil_parser import StructureEquilParserMaker
from atomate2.dmax.jobs.lammps_input_generation import DmaInputMaker  # import DMA input maker
from atomate2.dmax.jobs.dma_parser import DmaParserMaker  # import DMA parser maker
from atomate2 import SETTINGS
from atomate2.dmax.schemas.task import (
    DmaxDataGenerationFlowDocument,
    DmaxStructureEquilibrationFlowDocument,
    DmaxDmaFlowDocument,
)


@dataclass
class BaseDataGenerationFlow(Maker):
    """
    Flow for DMA data generation: structure generation and forcefield parametrization.

    Attributes:
        forcefield: Forcefield type ('opls', 'gaff2', 'auto').
        generator: Parametrization generator ('psp', 'foyer', 'pysimm', 'antechamber', 'auto').
    """
    # flow name
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
    forcefield: str = 'auto'
    generator: str = 'auto'

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
        ff_job = ForceFieldMaker(
            forcefield=self.forcefield,
            generator=self.generator,
            out_dir=wd,
        ).make(struct_job.output)

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

    Attributes:
        forcefield: Forcefield type ('opls', 'gaff2', 'auto').
        generator: Parametrization generator ('psp', 'foyer', 'pysimm', 'antechamber', 'auto').
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
    forcefield: str = 'auto'
    generator: str = 'auto'
    run_locally: bool = False

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
        ff_job = ForceFieldMaker(
            forcefield=self.forcefield,
            generator=self.generator,
            out_dir=wd,
        ).make(struct_job.output)

        # Generate LAMMPS input for structure equilibration
        from atomate2.dmax.jobs.lammps_input_generation import StructureEquilInputMaker
        input_job = StructureEquilInputMaker(
            name='structure_equilibration',
            data_file_type=ff_job.output.forcefield_type,
            out_dir=wd
        ).make(ff_job.output.data_file)

        # run the LAMMPS simulation: either local bash execution or SLURM
        local = self.run_locally or SETTINGS.LAMMPS_RUN_LOCALLY
        if local:
            run_job = LammpsLocalRunMaker().make(input_job.output)
        else:
            run_job = LammpsSlurmRunMaker().make(input_job.output)

        # parse the outputs: include input and run docs
        parse_job = StructureEquilParserMaker().make(input_job.output, run_job.output)

        # assemble final Flow document using direct OutputReferences
        struct_doc = struct_job.output
        ff_doc = ff_job.output
        input_doc = input_job.output
        run_doc = run_job.output
        doc = DmaxStructureEquilibrationFlowDocument(
            packmol_pdb=struct_doc.packmol_pdb,
            polymer_pdb=struct_doc.polymer_pdb,
            lammps_data=ff_doc.lammps_data,
            lammps_input=input_doc.input_file,
            slurm_file=input_doc.slurm_file,
            job_id=run_doc.job_id,
            restart_file=run_doc.restart_file,
        )
        # return flow chaining all jobs with consolidated document
        return Flow([
            struct_job,
            ff_job,
            input_job,
            run_job,
            parse_job,
        ], doc, name='structure_equilibration_flow')


@dataclass
class DmaFlow(Maker):
    """
    Flow that generates DMA input, runs LAMMPS, and parses DMA outputs.
    """
    name: str = 'dma_flow'
    run_locally: bool = False  # whether to run LAMMPS locally via bash script

    def make(self, restart_file: str) -> Flow:
        # generate input
        dma_input = DmaInputMaker().make(restart_file)
        dma_input.append_name(' input')
        # run LAMMPS: select SLURM or local based on run_locally or settings
        local = self.run_locally or SETTINGS.LAMMPS_RUN_LOCALLY
        if local:
            run_job = LammpsLocalRunMaker().make(dma_input.output)
        else:
            run_job = LammpsSlurmRunMaker().make(dma_input.output)
        run_job.append_name(' run')
        # parse outputs using the input and run documents
        parser_job = DmaParserMaker().make(dma_input.output, run_job.output)
        parser_job.append_name(' parse')
        # assemble and return the Flow directly
        return Flow(
            [dma_input, run_job, parser_job],
            output={
                'lammps_input': dma_input.output,
                'slurm_file': dma_input.output.slurm_file,
                'job_id': run_job.output.job_id,
                'restart_file': run_job.output.restart_file,
                'parser_output': parser_job.output,
            },
            name=self.name,
        )
