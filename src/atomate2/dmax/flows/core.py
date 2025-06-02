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
from atomate2.dmax.jobs.strain_convergence import StrainConvergencePlotMaker
from atomate2.dmax.jobs.lammps_input_generation import DmaInputMaker  # import DMA input maker
from atomate2.dmax.jobs.dma_parser import DmaParserMaker  # import DMA parser maker
from atomate2.dmax.jobs.error_analysis import ErrorAnalysisPlotMaker
from atomate2 import SETTINGS
from atomate2.dmax.schemas.task import (
    DmaxDataGenerationFlowDocument,
    DmaxStructureEquilibrationFlowDocument,
    DmaxDmaFlowDocument,
    DmaxStrainSizeConvergenceFlowDocument,
    DmaxNumCyclesConvergenceFlowDocument,
    DmaxErrorAnalysisFlowDocument,
    DmaxGlassTransitionFlowDocument,
)
from atomate2.dmax.jobs.num_cycles_convergence import NumCyclesConvergenceMaker
from atomate2.dmax.jobs.glass_transition import GlassTransitionPlotMaker
import numpy as np  # type: ignore
import matplotlib.pyplot as plt  # type: ignore


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


@dataclass
class StrainSizeConvergenceFlow(Maker):
    """
    Flow to test convergence of DMA results over varying oscillation amplitudes.
    """
    name: str = 'strain_size_convergence_flow'
    run_locally: bool = False
    n_amps: int = 5
    min_amp_pc: float = 0.1
    max_amp_pc: float = 50.0
    existing_dirs: dict[float, list[str]] | None = None  # optional mapping from amplitude to directories

    def make(self, restart_file: str) -> Flow:
        from atomate2.dmax.jobs.lammps_input_generation import DmaInputMaker
        from atomate2.dmax.jobs.lammps_slurm_run import LammpsSlurmRunMaker, LammpsLocalRunMaker
        from atomate2.dmax.jobs.dma_parser import DmaParserMaker
        parser_jobs: list = []
        all_jobs: list = []
        # if existing_dirs provided, parse those instead of launching new jobs
        if self.existing_dirs:
            from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
            amps = list(self.existing_dirs.keys())
            for amp in amps:
                for d in self.existing_dirs[amp]:
                    input_doc = DmaxLammpsInputDocument(
                        input_dir=d, data_file='', input_file='in.lammps', slurm_file=''
                    )
                    run_doc = DmaxLammpsRunDocument(
                        job_id='existing', restart_file=os.path.join(d, 'restart.equil')
                    )
                    parser_job = DmaParserMaker().make(input_doc, run_doc)
                    all_jobs.append(parser_job)
                    parser_jobs.append(parser_job)
        else:
            amps = np.linspace(self.min_amp_pc, self.max_amp_pc, self.n_amps)
            for amp in amps:
                dma_input_job = DmaInputMaker(osc_amp_pc=float(amp)).make(restart_file)
                all_jobs.append(dma_input_job)
                if self.run_locally or SETTINGS.LAMMPS_RUN_LOCALLY:
                    run_job = LammpsLocalRunMaker().make(dma_input_job.output)
                else:
                    run_job = LammpsSlurmRunMaker().make(dma_input_job.output)
                all_jobs.append(run_job)
                parser_job = DmaParserMaker().make(dma_input_job.output, run_job.output)
                all_jobs.append(parser_job)
                parser_jobs.append(parser_job)
        # post-process: plot and select optimal using a dedicated job
        amps_list = amps if isinstance(amps, list) else amps.tolist()
        plot_maker = StrainConvergencePlotMaker()
        conv_job = plot_maker.make([pj.output for pj in parser_jobs], amps_list)
        all_jobs.append(conv_job)
        return Flow(all_jobs, conv_job.output, name=self.name)


@dataclass
class NumCyclesConvergenceFlow(Maker):
    """
    Flow that re-parses a DMA run and analyzes tanδ convergence over cycle count.
    """
    name: str = 'num_cycles_convergence_flow'
    threshold: float = 0.01

    def make(self, restart_file: str) -> Flow:
        from atomate2.dmax.jobs.dma_parser import DmaParserMaker
        from atomate2.dmax.jobs.num_cycles_convergence import NumCyclesConvergenceMaker
        from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
        # work directory
        work_dir = os.path.dirname(restart_file)
        # full parse
        input_doc = DmaxLammpsInputDocument(
            input_dir=work_dir,
            data_file='', input_file='in.lammps', slurm_file=''
        )
        run_doc = DmaxLammpsRunDocument(job_id='local', restart_file=restart_file)
        full_parse = DmaParserMaker().make(input_doc, run_doc)
        full_parse.append_name(' full_parse')
        # cycle convergence
        cycle_job = NumCyclesConvergenceMaker(threshold=self.threshold).make(work_dir)
        cycle_job.append_name(' cycle_conv')
        # assemble
        return Flow(
            [full_parse, cycle_job],
            output={
                'full_parser': full_parse.output,
                'cycle_convergence': cycle_job.output,
            },
            name=self.name,
        )


@dataclass
class ErrorAnalysisFlow(Maker):
    """
    Flow to perform error analysis of DMA at different frequencies.
    """
    name: str = 'error_analysis_flow'
    osc_amp_pc: float = 25.0
    num_cycles: int = 5
    freqs_ghz: list[float] = field(default_factory=lambda: [20.0, 30.0, 40.0])
    n_sims: int = 5
    run_locally: bool = False
    existing_dirs: dict[float, list[str]] | None = None  # map frequency to list of dirs with existing runs

    def make(self, restart_file: str | None = None) -> Flow:
        all_jobs: list = []
        parser_groups: list[list] = []
        # if user provided existing directories, parse without running new sims
        if self.existing_dirs:
            freqs = list(self.existing_dirs.keys())
            from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
            for freq, dirs in self.existing_dirs.items():
                group = []
                for d in dirs:
                    # construct input/run docs pointing to existing run dir
                    input_doc = DmaxLammpsInputDocument(
                        input_dir=d, data_file='', input_file='in.lammps', slurm_file=''
                    )
                    run_doc = DmaxLammpsRunDocument(job_id='existing', restart_file=os.path.join(d, 'restart.equil'))
                    parser = DmaParserMaker().make(input_doc, run_doc)
                    all_jobs.append(parser)
                    group.append(parser)
                parser_groups.append(group)
        else:
            freqs = self.freqs_ghz
            for freq in freqs:
                freq_group = []
                for i in range(self.n_sims):
                    dma_input = DmaInputMaker(
                        osc_amp_pc=self.osc_amp_pc,
                        num_cycles=self.num_cycles,
                        frequency=freq * 1e9,
                        error_analysis=True,
                    ).make(restart_file)  # type: ignore
                    all_jobs.append(dma_input)
                    run_job = (
                        LammpsLocalRunMaker() if self.run_locally or SETTINGS.LAMMPS_RUN_LOCALLY
                        else LammpsSlurmRunMaker()
                    ).make(dma_input.output)
                    all_jobs.append(run_job)
                    parser = DmaParserMaker().make(dma_input.output, run_job.output)
                    all_jobs.append(parser)
                    freq_group.append(parser)
                parser_groups.append(freq_group)
        # plot error metrics
        plot_job = ErrorAnalysisPlotMaker().make(
            [[p.output for p in group] for group in parser_groups], freqs
        )
        all_jobs.append(plot_job)
        return Flow(all_jobs, plot_job.output, name=self.name)


@dataclass
class GlassTransitionTemperatureFlow(Maker):
    """Flow to estimate glass transition temperature from DMA across temperatures"""
    name: str = 'glass_transition_flow'
    osc_amp_pc: float = 25.0  # use optimal defaults
    num_cycles: int = 3
    frequency_ghz: float = 80.0
    temp_range: tuple[float, float] = (200.0, 400.0)  # plausible Tg range in K
    n_temps: int = 9  # provides ~25K spacing over 200-400K
    run_locally: bool = False
    existing_dirs: dict[float, list[str]] | None = None  # optional mapping from temperature to directories

    def make(self, restart_file: str | None = None) -> Flow:
        all_jobs: list = []
        parser_jobs: list = []
        # determine temperature list
        if self.existing_dirs:
            temps = list(self.existing_dirs.keys())
            from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
            for T in temps:
                for d in self.existing_dirs[T]:
                    input_doc = DmaxLammpsInputDocument(
                        input_dir=d, data_file='', input_file='in.lammps', slurm_file=''
                    )
                    run_doc = DmaxLammpsRunDocument(job_id='existing', restart_file=os.path.join(d, 'restart.equil'))
                    parser = DmaParserMaker().make(input_doc, run_doc)
                    all_jobs.append(parser)
                    parser_jobs.append(parser)
        else:
            temps = list(np.linspace(self.temp_range[0], self.temp_range[1], self.n_temps))
            for T in temps:
                # spawn DMA flows at each temperature
                dma_input = DmaInputMaker(
                    osc_amp_pc=self.osc_amp_pc,
                    num_cycles=self.num_cycles,
                    frequency=self.frequency_ghz * 1e9,
                ).make(restart_file)  # type: ignore
                all_jobs.append(dma_input)
                # modify temperature in the input script: will be picked up by parser if included in DmaInputMaker
                run_job = (
                    LammpsLocalRunMaker() if self.run_locally or SETTINGS.LAMMPS_RUN_LOCALLY
                    else LammpsSlurmRunMaker()
                ).make(dma_input.output)
                all_jobs.append(run_job)
                parser = DmaParserMaker().make(dma_input.output, run_job.output)
                all_jobs.append(parser)
                parser_jobs.append(parser)
        # plot Tg
        plot_job = GlassTransitionPlotMaker().make([p.output for p in parser_jobs], temps)
        all_jobs.append(plot_job)
        return Flow(all_jobs, plot_job.output, name=self.name)
