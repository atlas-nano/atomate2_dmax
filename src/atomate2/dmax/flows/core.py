"""
Flow for Dynamic Mechanical Analysis (DMA) simulations.

Chains structure generation and forcefield parametrization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from jobflow import Flow, Maker # include Response for DMA flow

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
from atomate2.dmax.jobs.lammps_run import LammpsRunMaker
from atomate2.dmax.jobs.structure_equil_parser import StructureEquilParserMaker
from atomate2.dmax.jobs.strain_convergence import StrainConvergencePlotMaker
from atomate2.dmax.jobs.lammps_input_generation import DmaInputMaker  # import DMA input maker
from atomate2.dmax.jobs.dma_parser import DmaParserMaker  # import DMA parser maker
from atomate2.dmax.jobs.error_analysis import ErrorAnalysisPlotMaker
from atomate2.dmax.settings import DMAX_SETTINGS
from atomate2.dmax.schemas.task import (
    DmaxDataGenerationFlowDocument,
    DmaxStructureEquilibrationFlowDocument,
    DmaxDmaFlowDocument,
    DmaxStrainSizeConvergenceFlowDocument,
    DmaxNumCyclesConvergenceFlowDocument,
    DmaxErrorAnalysisFlowDocument,
    DmaxGlassTransitionFlowDocument,
    DmaxMasterCurveFlowDocument,
)
from atomate2.dmax.jobs.glass_transition import GlassTransitionPlotMaker
from atomate2.dmax.jobs.master_curve import MasterCurvePlotMaker
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
    left_cap: str = "C[*]"
    right_cap: str = "C[*]"
    length: int = 10
    num_molecules: int = 5
    density: float = 0.8
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False
    forcefield: str = 'auto'
    generator: str = 'auto'
    include_impropers: bool = False

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
        struct_job.config.manager_config["_category"] = "local" 
        # forcefield
        ff_job = ForceFieldMaker(
            forcefield=self.forcefield,
            generator=self.generator,
            include_impropers=self.include_impropers,
            out_dir=wd,
        ).make(struct_job.output)
        ff_job.config.manager_config["_category"] = "local" 
        # assemble final document using task documents from each job
        struct_doc = struct_job.output  # DmaxStructureTaskDocument
        ff_doc = ff_job.output  # DmaxForceFieldTaskDocument
        doc = DmaxDataGenerationFlowDocument(
            packmol_pdb=struct_doc.packmol_pdb,
            polymer_pdb=struct_doc.polymer_pdb,
            data_file=ff_doc.data_file,
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

    include_impropers: bool = False  # whether to include improper dihedrals in forcefield

    # inherit or re-specify relevant parameters
    smiles: str = "[*]CC[*]"
    left_cap: str = "C[*]"
    right_cap: str = "C[*]"
    length: int = 10
    num_molecules: int = 5
    density: float = 0.8
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False
    forcefield: str = 'auto'
    generator: str = 'auto'
    include_impropers: bool = False
    heat_steps: int = 10000
    npt_steps: int = 30000
    prod_steps: int = 10000
    temperature: int = 300
    timestep: float = 1.0
    pressure: float = 1.0
    run_locally: bool = False
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(self) -> Flow:
        # 1) generate structure and forcefield
        data_flow = BaseDataGenerationFlow(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=self.out_dir,
            num_conf=self.num_conf,
            loop=self.loop,
            forcefield=self.forcefield,
            generator=self.generator,
            include_impropers=self.include_impropers,
        ).make()

        # 2) generate LAMMPS input for structure equilibration
        from atomate2.dmax.jobs.lammps_input_generation import StructureEquilInputMaker
        # generate LAMMPS input for structure equilibration using correct data file path
        input_job = StructureEquilInputMaker(
            name='structure_equilibration',
            out_dir=str(self.out_dir) if self.out_dir else None,
            heat_steps=self.heat_steps,
            npt_steps=self.npt_steps,
            prod_steps=self.prod_steps,
            temperature=self.temperature,
            timestep=self.timestep,
            pressure=self.pressure,
        ).make(data_flow.output.data_file)
        input_job.config.manager_config["_category"] = "local"  

        # run the LAMMPS simulation: either local bash execution or SLURM
        run_job = LammpsRunMaker().make(input_job.output)
        run_job.config.manager_config["_category"] = "hpc"

        # parse the outputs: include input and run docs
        parse_job = StructureEquilParserMaker().make(input_job.output, run_job.output)
        parse_job.config.manager_config["_category"] = "local"  
        # assemble final Flow document using data_flow output
        struct_doc = data_flow.output
        ff_doc = data_flow.output
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
            data_flow,
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
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(self, restart_file: str) -> Flow:
        # generate input
        dma_input = DmaInputMaker().make(restart_file)
        dma_input.append_name(' input')
        dma_input.config.manager_config["_category"] = "local" 
        # run LAMMPS: select SLURM or local based on run_locally or settings
        run_job = LammpsRunMaker().make(dma_input.output)
        run_job.config.manager_config["_category"] = "hpc"
        # parse outputs using the input and run documents
        parser_job = DmaParserMaker().make(dma_input.output, run_job.output)
        parser_job.append_name(' parse')
        parser_job.config.manager_config["_category"] = "local"  
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
    n_amps: int = 2
    min_amp_pc: float = 0.1
    max_amp_pc: float = 100.0
    existing_dirs: dict[float, list[str]] | None = None  # optional mapping from amplitude to directories
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(self, restart_file: str) -> Flow:
        from atomate2.dmax.jobs.lammps_input_generation import DmaInputMaker
        from atomate2.dmax.jobs.dma_parser import DmaParserMaker
        parser_jobs: list = []
        all_jobs: list = []
        restart_refs: list = []
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
                    parser_job.config.manager_config["_category"] = "local" 
                    all_jobs.append(parser_job)
                    parser_jobs.append(parser_job)
                    restart_refs.append(run_doc.restart_file)
        else:
            amps = np.linspace(self.min_amp_pc, self.max_amp_pc, self.n_amps)
            for amp in amps:
                dma_input_job = DmaInputMaker(osc_amp_pc=float(amp)).make(restart_file)
                dma_input_job.config.manager_config["_category"] = "local"
                all_jobs.append(dma_input_job)

                run_job = LammpsRunMaker().make(dma_input_job.output)
                run_job.config.manager_config["_category"] = "hpc"                    
                all_jobs.append(run_job)

                parser_job = DmaParserMaker().make(dma_input_job.output, run_job.output)
                parser_job.config.manager_config["_category"] = "local"                    
                all_jobs.append(parser_job)
                parser_jobs.append(parser_job)       
                restart_refs.append(run_job.output.restart_file)
        # post-process: plot and select optimal using a dedicated job
        amps_list = amps if isinstance(amps, list) else amps.tolist()
        plot_maker = StrainConvergencePlotMaker()
        conv_job = plot_maker.make(
            [pj.output for pj in parser_jobs],
            amps_list,
            restart_refs,                        
        )
        conv_job.config.manager_config["_category"] = "local" 
        all_jobs.append(conv_job)
        return Flow(all_jobs, conv_job.output, name=self.name)


@dataclass
class NumCyclesConvergenceFlow(Maker):
    """
    Flow that re-parses a DMA run and analyzes tan δ convergence over cycle count.

    Two jobs are launched:
      1) `full_parse`  · parses the entire DMA log (gives a rich record)
      2) `cycle_job`   · analyses tanδ vs. #cycles

    The second job receives BOTH the `restart_file` and `full_parse.output`.
    The latter is ignored inside the job but forces a dependency, so the
    scheduler now knows `cycle_job` must start **after** `full_parse`.
    """
    name: str = 'num_cycles_convergence_flow'
    threshold: float = 0.01

    def make(self, restart_file: Any) -> Flow:
        # ------------------------------------------------------------------ #
        # 1) Build the full parser job (needs the working directory)
        # ------------------------------------------------------------------ #
        restart_path = str(restart_file)
        work_dir = os.path.dirname(restart_path)

        from atomate2.dmax.jobs.dma_parser import DmaParserMaker
        from atomate2.dmax.jobs.num_cycles_convergence import NumCyclesConvergenceMaker
        from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument

        input_doc = DmaxLammpsInputDocument(
            input_dir=work_dir,
            data_file='',
            input_file='in.lammps',
            slurm_file='',
        )
        run_doc = DmaxLammpsRunDocument(job_id='local', restart_file=restart_path)

        full_parse = DmaParserMaker().make(input_doc, run_doc)
        full_parse.config.manager_config["_category"] = "local" 
        full_parse.append_name(' full_parse')

        # ------------------------------------------------------------------ #
        # 2) Cycle-convergence analysis -- depends on full_parse
        # ------------------------------------------------------------------ #
        cycle_job = NumCyclesConvergenceMaker(threshold=self.threshold).make(
            restart_file,           # real input
            full_parse.output       # *unused* but adds an edge
        )
        cycle_job.config.manager_config["_category"] = "local" 
        cycle_job.append_name(' cycle_conv')

        # ------------------------------------------------------------------ #
        # 3) Assemble Flow
        # ------------------------------------------------------------------ #
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
    num_cycles: int = 2
    freqs_ghz: list[float] = field(default_factory=lambda: [400.0, 450.0])  # default frequencies in GHz
    n_sims: int = 2
    run_locally: bool = False
    existing_dirs: dict[float, list[str]] | None = None  # map frequency to list of dirs with existing runs
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

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
                    parser.config.manager_config["_category"] = "local" 
                    all_jobs.append(parser)
                    group.append(parser)
                parser_groups.append(group)
        else:
            freqs = self.freqs_ghz
            for freq in freqs:
                freq_group = []
                for i in range(self.n_sims):
                    dma_input = (
                        DmaInputMaker(
                            frequency=freq * 1e9,
                            error_analysis=True,
                        )
                        .make(restart_file, self.num_cycles, osc_amp_pc=self.osc_amp_pc)
                    )
                    dma_input.config.manager_config["_category"] = "local"
                    all_jobs.append(dma_input)
                    run_job = LammpsRunMaker().make(dma_input.output)
                    run_job.config.manager_config["_category"] = "hpc"
                    all_jobs.append(run_job)
                    parser = DmaParserMaker().make(dma_input.output, run_job.output)
                    parser.config.manager_config["_category"] = "local" 
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
    num_cycles: int = 2
    frequency_ghz: float = 400.0
    temp_range: tuple[float, float] = (200.0, 400.0)  # plausible Tg range in K
    n_temps: int = 2  # provides ~25K spacing over 200-400K
    run_locally: bool = False
    existing_dirs: dict[float, list[str]] | None = None  # optional mapping from temperature to directories
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(
        self,
        restart_file: str,
        *,                          # keyword-only
        after: Any | None = None,   # ← NEW, completely ignored inside
    ) -> Flow:
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
                    parser.config.manager_config["_category"] = "local" 
                    all_jobs.append(parser)
                    parser_jobs.append(parser)
        else:
            temps = list(np.linspace(self.temp_range[0], self.temp_range[1], self.n_temps))
            for T in temps:
                # spawn DMA runs at specified temperature T
                dma_input = (
                    DmaInputMaker(
                        frequency=self.frequency_ghz * 1e9,
                        temperature=T,
                    )
                    .make(restart_file, self.num_cycles, osc_amp_pc=self.osc_amp_pc, after=after)
                )
                dma_input.config.manager_config["_category"] = "local"
                all_jobs.append(dma_input)
                # modify temperature in the input script: will be picked up by parser if included in DmaInputMaker
                run_job = LammpsRunMaker().make(dma_input.output)
                run_job.config.manager_config["_category"] = "hpc"
                all_jobs.append(run_job)
                parser = DmaParserMaker().make(dma_input.output, run_job.output)
                parser.config.manager_config["_category"] = "local" 
                all_jobs.append(parser)
                parser_jobs.append(parser)
        # plot Tg
        plot_job = GlassTransitionPlotMaker().make([p.output for p in parser_jobs], temps)
        plot_job.config.manager_config["_category"] = "local" 
        all_jobs.append(plot_job)
        return Flow(all_jobs, plot_job.output, name=self.name)


@dataclass
class MasterCurveFlow(Maker):
    """Flow to construct a master curve over temperatures and frequencies"""
    name: str = 'master_curve_flow'
    osc_amp_pc: float = 25.0
    num_cycles: int = 2
    reference_temp: float | None = None
    temp_range: tuple[float, float] = (200.0, 400.0)
    n_temps: int = 5
    freqs_ghz: list[float] = field(default_factory=lambda: list(np.logspace(np.log10(10.0), np.log10(100.0), 3)))
    run_locally: bool = False
    existing_dirs: dict[tuple[float, float], list[str]] | None = None
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(
        self,
        restart_file: str,
        *,                          # keyword-only
        after: Any | None = None,   # ← NEW
    ) -> Flow:
        all_jobs: list = []
        parser_outputs: list = []
        # determine temperatures and reference
        if self.reference_temp is None:
            temps = list(np.linspace(self.temp_range[0], self.temp_range[1], self.n_temps))
            ref_temp = sum(self.temp_range) / 2.0
        else:
            temps = list(np.linspace(self.temp_range[0], self.temp_range[1], self.n_temps))
            ref_temp = self.reference_temp
        freqs = self.freqs_ghz
        from atomate2.dmax.schemas.task import DmaxLammpsInputDocument, DmaxLammpsRunDocument
        for T in temps:
            for fghz in freqs:
                key = (T, fghz)
                if self.existing_dirs and key in self.existing_dirs:
                    for d in self.existing_dirs[key]:
                        input_doc = DmaxLammpsInputDocument(input_dir=d, data_file='', input_file='in.lammps', slurm_file='')
                        run_doc = DmaxLammpsRunDocument(job_id='existing', restart_file=os.path.join(d, 'restart.equil'))
                        parser = DmaParserMaker().make(input_doc, run_doc)
                        parser.config.manager_config["_category"] = "local" 
                        all_jobs.append(parser)
                        parser_outputs.append(parser.output)
                else:
                    dma_input = (
                        DmaInputMaker(
                            frequency=fghz * 1e9,
                            temperature=T,
                        )
                        .make(restart_file, self.num_cycles, osc_amp_pc=self.osc_amp_pc, after=after)
                    )
                    all_jobs.append(dma_input)
                    dma_input.config.manager_config["_category"] = "local"
                    run_job = LammpsRunMaker().make(dma_input.output)
                    run_job.config.manager_config["_category"] = "hpc"
                    all_jobs.append(run_job)
                    parser = DmaParserMaker().make(dma_input.output, run_job.output)
                    parser.config.manager_config["_category"] = "local" 
                    all_jobs.append(parser)
                    parser_outputs.append(parser.output)
        # plot master curve
        plot_job = MasterCurvePlotMaker(
            freqs_GHz=freqs,
            temps_K=temps,
            reference_temp_K=ref_temp,
        ).make(parser_outputs)
        plot_job.config.manager_config["_category"] = "local" 
        all_jobs.append(plot_job)
        return Flow(all_jobs, plot_job.output, name=self.name)


@dataclass
class FullGlassTemperatureFlow(Maker):
    """Run full workflow up to glass transition analysis"""
    # flow parameters
    name: str = 'full_glass_temperature_flow'
    # polymer structure parameters
    smiles: str = "[*]CC[*]"
    left_cap: str = "C[*]"
    right_cap: str = "C[*]"
    length: int = 10
    num_molecules: int = 5
    density: float = 1.0
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False
    forcefield: str = 'auto'
    generator: str = 'auto'
    include_impropers: bool = False
    # convergence parameters for strain-size
    n_amps: int = 2
    min_amp_pc: float = 0.1
    max_amp_pc: float = 50.0
    existing_dirs: dict[float, list[str]] | None = None
    # execution parameters
    run_locally: bool = False
    error_freqs_ghz: list[float] = field(default_factory=lambda: list(np.linspace(0.1, 100.0, 2)))
    error_n_sims: int = 2
    temp_range: tuple[float, float] = (200.0, 400.0)  # temperature range for glass transition
    n_temps: int = 2  # number of temperatures to sample for glass transition
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU

    def make(self) -> Flow:
        # 2) structure equilibration
        struct_flow = StructureEquilibrationFlow(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=self.out_dir,
            num_conf=self.num_conf,
            loop=self.loop,
            forcefield=self.forcefield,
            generator=self.generator,
            run_locally=self.run_locally,
            include_impropers=self.include_impropers,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make()
        # 3) get restart file reference for downstream jobs
        restart = struct_flow.output.restart_file
        # 4) strain convergence
        strain_flow = StrainSizeConvergenceFlow(
            run_locally=self.run_locally,
            n_amps=self.n_amps,
            min_amp_pc=self.min_amp_pc,
            max_amp_pc=self.max_amp_pc,
            existing_dirs=self.existing_dirs,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart)
        optimal_amp = strain_flow.output.optimal_osc_amp_pc
        # 5) cycles convergence
        #num_flow = NumCyclesConvergenceFlow(threshold=0.01).make(restart)
        #optimal_cycles = num_flow.output['cycle_convergence'].optimal_num_cycles
        # 6) error analysis
        error_flow = ErrorAnalysisFlow(
            osc_amp_pc=optimal_amp,
            freqs_ghz=self.error_freqs_ghz,
            n_sims=self.error_n_sims,
            run_locally=self.run_locally,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart)
        # 7) glass transition
        glass_flow = GlassTransitionTemperatureFlow(
            osc_amp_pc=optimal_amp,
            run_locally=self.run_locally,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
            temp_range=self.temp_range,
            n_temps=self.n_temps,
        ).make(restart)
        # assemble
        return Flow(
            [struct_flow, strain_flow, error_flow, glass_flow],
            glass_flow.output,
            name=self.name,
        )


@dataclass
class FullDmaxFlow(FullGlassTemperatureFlow):
    """Run full DMAx workflow including master curve construction"""
    name: str = 'full_dmax_flow'
    # GPU settings (inherited polymer and execution parameters available)
    use_gpu: bool = False  # whether to use GPU for LAMMPS runs
    gpu_count: int = 1  # number of GPUs to use if using GPU
    # master curve parameters
    reference_temp: float | None = None
    temp_range: tuple[float, float] = (200.0, 400.0)
    n_temps: int = 2
    freqs_ghz: list[float] = field(default_factory=lambda: list(np.logspace(np.log10(10.0), np.log10(100.0), 2)))
    existing_dirs: dict[tuple[float, float], list[str]] | None = None  # optional pre-run directories

    def make(self) -> Flow:
        # 1) structure equilibration (includes data generation)
        struct_flow = StructureEquilibrationFlow(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=self.out_dir,
            num_conf=self.num_conf,
            loop=self.loop,
            forcefield=self.forcefield,
            generator=self.generator,
            include_impropers=self.include_impropers,
            run_locally=self.run_locally,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make()
        # 2) get restart file reference for downstream jobs
        restart = struct_flow.output.restart_file
        # 3) strain convergence
        strain_flow = StrainSizeConvergenceFlow(
            run_locally=self.run_locally,
            n_amps=self.n_amps,
            min_amp_pc=self.min_amp_pc,
            max_amp_pc=self.max_amp_pc,
            existing_dirs=self.existing_dirs,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart)
        optimal_amp = strain_flow.output.optimal_osc_amp_pc
        # 4) cycles convergence
        optimal_cycles = strain_flow.output.optimal_num_cycles
        # 5) error analysis
        error_flow = ErrorAnalysisFlow(
            osc_amp_pc=optimal_amp,
            num_cycles=optimal_cycles,
            freqs_ghz=self.error_freqs_ghz,
            n_sims=self.error_n_sims,
            run_locally=self.run_locally,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart)
        # 6) glass transition
        glass_flow = GlassTransitionTemperatureFlow(
            osc_amp_pc=optimal_amp,
            num_cycles=optimal_cycles,
            run_locally=self.run_locally,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart, after=error_flow.output)
        # 7) master curve construction
        # determine reference temperature for master curve
        ref_temp = self.reference_temp or glass_flow.output.glass_transition_temp
        master_flow = MasterCurveFlow(
            osc_amp_pc=optimal_amp,
            num_cycles=optimal_cycles,
            reference_temp=ref_temp,
            temp_range=self.temp_range,
            n_temps=self.n_temps,
            freqs_ghz=self.freqs_ghz,
            run_locally=self.run_locally,
            existing_dirs=self.existing_dirs,
            use_gpu=self.use_gpu,
            gpu_count=self.gpu_count,
        ).make(restart, after=glass_flow.output)
        # assemble full workflow
        return Flow(
            [struct_flow, strain_flow, error_flow, glass_flow, master_flow],
            master_flow.output,
            name=self.name,
        )
