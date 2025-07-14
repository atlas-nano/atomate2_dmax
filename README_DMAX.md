# Atomate2-DMAx: Polymer Molecular Dynamics Workflows

Atomate2-DMAx extends the atomate2 framework with specialized workflows for polymer molecular dynamics simulations and dynamic mechanical analysis (DMA). This package enables high-throughput computational studies of polymer properties through automated structure generation, force field parameterization, and property prediction.

## Key Features

- **Automated Polymer Structure Generation**: Interface with PolymerStructurePredictor (PSP) for building amorphous polymer structures
- **Force Field Parameterization**: Support for OPLS-AA via LigParGen and other force fields via Foyer
- **LAMMPS Integration**: Automated generation and execution of LAMMPS molecular dynamics simulations
- **Dynamic Mechanical Analysis**: Glass transition temperature prediction and viscoelastic property analysis
- **Error Analysis**: Convergence studies and statistical analysis of simulation results
- **High-throughput Workflows**: Scalable workflows using the JobFlow framework

## Quick Start

### Installation

Choose one of the following installation methods:

#### Option 1: Automated Installation (Recommended)
```bash
# Clone the repository
git clone https://github.com/rsilvabuarque/atomate2_dmax.git
cd atomate2_dmax

# Run the automated installation script
./install_atomate2_dmax.sh

# Activate the environment
source ~/atomate2_config/atomate2_env.sh
```

#### Option 2: Using Conda Environment File
```bash
# Create environment from file
conda env create -f environment.yml
conda activate atomate2_dmax

# Install additional dependencies
./quick_setup.sh
```

#### Option 3: Manual Installation
See the detailed [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step instructions.

### Basic Usage

```python
from atomate2.dmax.flows.core import StructureEquilibrationMaker
from atomate2.dmax.jobs.structure_generation import PSPStructureMaker

# Create a polymer structure
structure_maker = PSPStructureMaker(
    smiles="[*]CC[*]",  # Polyethylene
    length=20,          # 20 monomers per chain
    num_molecules=50,   # 50 chains
    density=0.85        # g/cm³
)

# Create equilibration workflow
equil_maker = StructureEquilibrationMaker()
workflow = equil_maker.make()

# Run the workflow (requires JobFlow setup)
from jobflow import run_locally
run_locally(workflow)
```

## Core Components

### Structure Generation
- **PSPStructureMaker**: Generate amorphous polymer structures using PSP
- Support for various polymer chemistries via SMILES notation
- Configurable chain length, density, and box dimensions

### Force Field Parameterization
- **ForceFieldMaker**: Automated force field assignment
- OPLS-AA support via LigParGen integration
- Generic force field support via Foyer/GMSO
- Custom force field parameter handling

### Molecular Dynamics Simulations
- **LammpsRunMaker**: Execute LAMMPS simulations
- **DmaInputMaker**: Generate DMA-specific input files
- Support for various ensembles (NVT, NPT, etc.)
- Automated temperature and strain protocols

### Analysis Tools
- **DmaParserMaker**: Extract viscoelastic properties from MD trajectories
- **GlassTransitionPlotMaker**: Determine glass transition temperatures
- **ErrorAnalysisPlotMaker**: Convergence and uncertainty analysis
- **MasterCurvePlotMaker**: Time-temperature superposition analysis

### Workflows
- **StructureEquilibrationMaker**: Complete structure generation and equilibration
- **DynamicMechanicalAnalysisMaker**: DMA property prediction workflows
- **ErrorAnalysisMaker**: Statistical analysis workflows

## Dependencies

### Core Dependencies
- Python ≥ 3.10
- atomate2 core packages (jobflow, pymatgen, etc.)
- NumPy, SciPy, pandas, matplotlib
- ASE (Atomic Simulation Environment)
- MDAnalysis

### Molecular Dynamics Dependencies
- LAMMPS (molecular dynamics engine)
- OpenBabel (chemical toolkit)
- RDKit (cheminformatics)

### Force Field Dependencies
- mbuild (molecular building)
- foyer (force field assignment)
- GMSO (general molecular simulation objects)
- forcefield-utilities

### External Dependencies
- **PolymerStructurePredictor (PSP)**: Required for polymer structure generation
  - Install from: https://github.com/rsilvabuarque/PSP_mod
- **BOSS Database**: Optional, for additional force field parameters

## Configuration

### Database Setup
Configure MongoDB for storing workflow results:

```yaml
# jobflow.yaml
JOB_STORE:
  docs_store:
    type: MongoStore
    host: "your_mongodb_host"
    database: "your_database"
    # ... additional settings
```

### Computational Settings
Configure LAMMPS and other computational settings:

```yaml
# atomate2.yaml
LAMMPS_CMD: "lmp_serial"
LAMMPS_RUN_COMMAND: "lmp_serial"
STORE_TRAJECTORY: true
# ... additional settings
```

### Environment Variables
```bash
export ATOMATE2_CONFIG_FILE="~/atomate2_config/atomate2.yaml"
export JOBFLOW_CONFIG_FILE="~/atomate2_config/jobflow.yaml"
```

## Example Workflows

### Polymer Glass Transition Study
```python
from atomate2.dmax.flows.core import DynamicMechanicalAnalysisMaker

# Create DMA workflow for glass transition analysis
dma_maker = DynamicMechanicalAnalysisMaker(
    polymer_smiles="[*]CC(C)[*]",  # Polypropylene
    temperatures=[200, 250, 300, 350, 400],  # K
    strain_rates=[1e-4, 1e-3, 1e-2],  # 1/ps
    chain_length=30,
    num_chains=100
)

workflow = dma_maker.make()
```

### Force Field Comparison Study
```python
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker

# Compare different force field methods
ff_makers = [
    ForceFieldMaker(method="ligpargen", ff_name="opls"),
    ForceFieldMaker(method="foyer", ff_name="oplsaa"),
    ForceFieldMaker(method="foyer", ff_name="gaff2")
]

# Use in comparative workflow...
```

## Testing

Verify your installation:

```bash
# Test basic imports
python test_installation.py

# Test workflow creation
python test_workflow.py

# Run unit tests (if available)
pytest tests/dmax/
```

## Documentation

- [Setup Guide](SETUP_GUIDE.md): Detailed installation instructions
- [User Guide](docs/user/codes/dmax.md): Comprehensive usage documentation
- [API Reference](docs/reference/): Complete API documentation
- [Examples](tutorials/): Jupyter notebook tutorials

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

- [GitHub Issues](https://github.com/rsilvabuarque/atomate2_dmax/issues): Bug reports and feature requests
- [Atomate2 Documentation](https://materialsproject.github.io/atomate2/): General atomate2 documentation
- [JobFlow Documentation](https://materialsproject.github.io/jobflow/): Workflow framework documentation

## Citation

If you use atomate2-dmax in your research, please cite:

```
@software{atomate2_dmax,
  title = {Atomate2-DMAx: Polymer Molecular Dynamics Workflows},
  author = {Silva Buarque, R. and others},
  url = {https://github.com/rsilvabuarque/atomate2_dmax},
  year = {2024}
}
```

Also cite the underlying packages:
- [Atomate2](https://materialsproject.github.io/atomate2/)
- [JobFlow](https://materialsproject.github.io/jobflow/)
- [Pymatgen](https://pymatgen.org/)
- [LAMMPS](https://lammps.sandia.gov/)

## License

This project is licensed under the same modified BSD license as atomate2.

## Acknowledgments

- Materials Project for the atomate2 framework
- PolymerStructurePredictor developers
- LAMMPS developers
- All contributors to the molecular simulation ecosystem
