import math
from dataclasses import dataclass, asdict, field
from pathlib import Path
from jobflow import Maker, job
import os, shutil
from jinja2 import Environment, FileSystemLoader

from atomate2.dmax.schemas.task import DmaxLammpsInputDocument

# Directory containing Jinja2 templates
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates' / 'lammps'

def render_template(template_name: str, context: dict, out_path: str):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )
    template = env.get_template(template_name)
    rendered = template.render(**context)
    with open(out_path, 'w') as f:
        f.write(rendered)

@dataclass
class LammpsInputMakerBase(Maker):
    """
    Base Maker for generating LAMMPS input files from a template.
    """
    name: str = ''
    # instead of template_name, select via simulation_type
    simulation_type: str = ''
    data_file_type: str = 'opls'
    slurm_ntasks: int = 1
    slurm_time: str = '01:00:00'
    out_dir: Path | None = None
    # whether to use GPU-specific SLURM template (slurm_gpu.sh)
    use_gpu: bool = False
    # actual Jobflow maker name must be defined
    # map simulation_type to template file
    SIM2TEMPLATE = {
        'structure equilibration': 'in.master_structure_equilibration',
        # both DMA error analysis and DMA simulation use the same template
        'error analysis': 'in.master_dynamic_mechanical_analysis',
        'dma simulation': 'in.master_dynamic_mechanical_analysis',
    }

    @job(output_schema=DmaxLammpsInputDocument)
    def make(self, data_file: str) -> DmaxLammpsInputDocument:
        # prepare working directory
        wd = os.getcwd()
        # copy LAMMPS data file; support absolute or relative (from parent) paths
        src = data_file
        if not os.path.isabs(src) or not os.path.exists(src):
            # try parent directory if src not found
            parent = os.path.abspath(os.path.join(wd, os.pardir))
            candidate = os.path.join(parent, os.path.basename(data_file))
            if os.path.exists(candidate):
                src = candidate
        dest_data = os.path.join(wd, os.path.basename(src))
        shutil.copy(src, dest_data)
        # determine template by simulation_type
        tpl = self.SIM2TEMPLATE[self.simulation_type]
        # build context from maker attributes
        ctx = asdict(self)
        # override system_name in context (replace spaces with underscores)
        ctx['system_name'] = self.name.replace(' ', '_')
        # always inject style defaults for OPLS/GAFF2
        style_defaults = {
            'opls': {
                'units': 'real',
                'atom_style': 'full',
                'pair_style': 'lj/cut/coul/long 10.0',
                'bond_style': 'harmonic',
                'angle_style': 'harmonic',
                'dihedral_style': 'opls',
                'improper_style': 'cvff',
                'kspace_style': 'pppm 1e-6',
                'pair_modify': 'mix arithmetic',
                'neighbor': '2.0 bin',
                'neigh_modify': 'every 2 delay 10 check yes',
                'thermo_style': 'custom step temp pe etotal',
            },
            'gaff2': {
                'units': 'real',
                'atom_style': 'full',
                'pair_style': 'lj/cut/coul/long 10.0',
                'bond_style': 'harmonic',
                'angle_style': 'harmonic',
                'dihedral_style': 'fourier',
                'improper_style': 'none',
                'kspace_style': 'pppm 1e-6',
                'pair_modify': 'mix geometric',
                'neighbor': '2.0 bin',
                'neigh_modify': 'every 2 delay 10 check yes',
                'thermo_style': 'custom step temp pe etotal',
            },
        }
        ctx.update(style_defaults.get(self.data_file_type, {}))
        # ensure full thermo_style listing for DMA simulations
        if self.simulation_type == 'dma simulation':
            ctx['thermo_style'] = (
                'custom step dt time etotal ecouple ke pe temp press pxx pyy pzz '
                'pxy pxz pyz lx ly lz vol density'
            )
        ctx['data_file'] = os.path.basename(data_file)
        input_fname = 'in.lammps'
        render_template(tpl, ctx, os.path.join(wd, input_fname))
        # render SLURM submission script (CPU or GPU)
        slurm_fname = 'lammps.slurm'
        slurm_context = {
            'job_name': self.name,
            'slurm_ntasks': self.slurm_ntasks,
            'slurm_time': self.slurm_time,
        }
        # choose template based on flag
        slurm_template = 'slurm_gpu.sh' if self.use_gpu else 'slurm.sh'
        # ensure SLURM template exists
        tpl_path = TEMPLATE_DIR / slurm_template
        if not tpl_path.exists():
            raise FileNotFoundError(
                f"SLURM template '{slurm_template}' not found in {TEMPLATE_DIR}. "
                "Please add your cluster-specific slurm.sh (and slurm_gpu.sh) templates to that directory or set use_gpu accordingly."
            )
        render_template(slurm_template, slurm_context, os.path.join(wd, slurm_fname))
        return DmaxLammpsInputDocument(
            input_dir=wd,
            data_file=os.path.basename(data_file),
            input_file=input_fname,
            slurm_file=slurm_fname,
        )

@dataclass
class StructureEquilInputMaker(LammpsInputMakerBase):
    name: str = 'structure_equilibration'
    simulation_type: str = 'structure equilibration'
    data_file_type: str = 'opls'
    # default non-style variables
    boundary: str = 'p p p'
    dielectric: float = 1.0
    special_bonds: str = 'lj/coul 0.0 0.0 0.0'
    system_name: str = 'system'
    timestep: float = 1.0
    temperature: float = 300.0
    pressure: float = 1.0
    heat_steps: int = 10000
    npt_steps: int = 10000
    prod_steps: int = 100000

@dataclass
class DmaInputMaker(LammpsInputMakerBase):
    name: str = 'dma'
    simulation_type: str = 'dma simulation'
    data_file_type: str = 'opls'
    # whether this is an error analysis run (random seed) or standard DMA
    error_analysis: bool = False
    # input restart is always required
    # DMA parameters
    timestep: float = 1.0
    temperature: float = 300.0
    pressure: float = 1.0
    # deformation axes (x, y, z); default to z, x, y
    dim_0: str = 'z'
    dim_1: str = 'x'
    dim_2: str = 'y'
    period: int = 0     # will be computed by frequency
    runtime: int = 0    # will be computed by num_cycles
    thermo: int = 0     # will be computed by num_cycles
    seed: int = 12345678
    frequency: float = 50e9  # oscillation frequency in Hz
    num_cycles: int = 3     # number of oscillation cycles to run
    osc_amp_pc: float = 20  # oscillation amplitude in percent of box length
    npt_steps: int = 10000

    @job(output_schema=DmaxLammpsInputDocument)
    def make(self, restart_file: str, data_file: str = None) -> DmaxLammpsInputDocument:
         # determine seed based on error_analysis flag
         if self.error_analysis:
             import random
             self.seed = random.randint(10**7, 10**8 - 1)
         # determine deformation axes from provided data file box dimensions
         if data_file:
             lengths = {}
             try:
                 with open(data_file, 'r') as df:
                     for line in df:
                         parts = line.strip().split()
                         if len(parts) == 4 and parts[2].endswith('lo') and parts[3].endswith('hi'):
                             axis = parts[2][0].lower()
                             lo, hi = float(parts[0]), float(parts[1])
                             lengths[axis] = hi - lo
                 # sort axes by length descending
                 if len(lengths) == 3:
                     sorted_axes = sorted(lengths.items(), key=lambda kv: kv[1], reverse=True)
                     self.dim_0, self.dim_1, self.dim_2 = [ax for ax, _ in sorted_axes]
             except Exception:
                 # fallback to defaults 'z','x','y'
                 pass
         # compute period, thermo, and total runtime in timesteps
         dt_s = self.timestep * 1e-15
         steps_per_period = math.ceil((1.0 / self.frequency) / dt_s)
         self.period = steps_per_period
         self.thermo = max(1, steps_per_period // 1000)
         self.runtime = steps_per_period * self.num_cycles
         # delegate to base class to copy restart file, render templates, and return document
         return LammpsInputMakerBase.make.__wrapped__(self, restart_file)
