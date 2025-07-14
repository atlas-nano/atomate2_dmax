# Troubleshooting Guide for Atomate2-DMAx

This guide helps resolve common issues encountered during installation and usage of atomate2-dmax.

## Installation Issues

### 1. Conda/Mamba Installation Problems

**Issue**: `conda command not found`
```bash
# Solutions:
# Option A: Load conda module (on HPC systems)
module load conda

# Option B: Initialize conda in your shell
conda init bash
source ~/.bashrc

# Option C: Use full path to conda
/path/to/miniconda3/bin/conda activate atomate2_dmax
```

**Issue**: Environment already exists
```bash
# Remove existing environment
conda remove --name atomate2_dmax --all

# Or use force flag with installation script
./install_atomate2_dmax.sh --force
```

**Issue**: Package conflicts during conda install
```bash
# Try using mamba instead of conda
conda install mamba -c conda-forge
mamba env create -f environment.yml

# Or create minimal environment and install packages individually
conda create -n atomate2_dmax python=3.10
conda activate atomate2_dmax
# Install packages one by one...
```

### 2. PSP (PolymerStructurePredictor) Issues

**Issue**: `ImportError: No module named 'psp'`
```bash
# Reinstall PSP
cd ~/atomate2_dmax_deps
rm -rf PSP
git clone https://github.com/rsilvabuarque/PSP_mod PSP
cd PSP
python setup.py install

# Verify installation
python -c "import psp.AmorphousBuilder; print('PSP OK')"
```

**Issue**: PSP installation fails
```bash
# Check Python and pip
which python
which pip

# Make sure you're in the correct environment
conda activate atomate2_dmax

# Try alternative installation
cd PSP
pip install -e .
```

**Issue**: PSP missing dependencies
```bash
# Install additional PSP dependencies
pip install rdkit-pypi
conda install -c conda-forge openbabel
```

### 3. Force Field Package Issues

**Issue**: `ImportError: No module named 'mbuild'` or similar
```bash
# Install missing molecular packages
conda install -c conda-forge mbuild foyer gmso forcefield-utilities

# If conda installation fails, try different channels
conda install -c conda-forge -c omnia mbuild
```

**Issue**: GMSO import errors
```bash
# GMSO might need specific versions
conda install -c conda-forge "gmso>=0.11.0"

# Or install from conda-forge specific channel
conda install -c conda-forge/label/gmso_dev gmso
```

### 4. LAMMPS Issues

**Issue**: `LAMMPS command not found`
```bash
# Install LAMMPS via conda
conda install -c conda-forge lammps

# Or install specific LAMMPS version
conda install -c conda-forge "lammps>=2023.08.02"

# Update atomate2.yaml with correct LAMMPS command
# LAMMPS_CMD: "lmp"  # or "lmp_serial", "lmp_mpi"
```

**Issue**: LAMMPS MPI issues
```bash
# For serial LAMMPS
conda install -c conda-forge lammps=*=serial*

# For MPI LAMMPS
conda install -c conda-forge lammps=*=mpi* mpi4py
```

## Configuration Issues

### 1. Environment Variables

**Issue**: Config files not found
```bash
# Check environment variables
echo $ATOMATE2_CONFIG_FILE
echo $JOBFLOW_CONFIG_FILE

# Set manually if needed
export ATOMATE2_CONFIG_FILE="$HOME/atomate2_config/atomate2.yaml"
export JOBFLOW_CONFIG_FILE="$HOME/atomate2_config/jobflow.yaml"

# Add to shell config for persistence
echo 'export ATOMATE2_CONFIG_FILE="$HOME/atomate2_config/atomate2.yaml"' >> ~/.bashrc
echo 'export JOBFLOW_CONFIG_FILE="$HOME/atomate2_config/jobflow.yaml"' >> ~/.bashrc
```

### 2. Database Connection Issues

**Issue**: MongoDB connection failed
```bash
# Test MongoDB connection
python -c "
import pymongo
client = pymongo.MongoClient('your_host', 27017)
print(client.list_database_names())
"
```

**Issue**: Authentication failed
```bash
# Check credentials in jobflow.yaml
# Make sure username/password are correct
# Verify database permissions
```

**Issue**: Database not accessible
```bash
# For local testing, use simple file-based store
# Edit jobflow.yaml:
JOB_STORE:
  docs_store:
    type: MemoryStore
```

## Runtime Issues

### 1. Import Errors

**Issue**: `ImportError: cannot import name 'X' from 'atomate2.dmax'`
```bash
# Reinstall atomate2_dmax
cd ~/atomate2_dmax_deps/atomate2_dmax
git pull origin feature/dmax2-lammps
pip install -e . --force-reinstall

# Check installation
python -c "import atomate2.dmax; print('DMAx OK')"
```

### 2. Workflow Execution Issues

**Issue**: Jobs fail with file not found errors
```bash
# Check working directory permissions
ls -la

# Ensure LAMMPS templates are accessible
python -c "
import atomate2.dmax
import os
template_dir = os.path.join(os.path.dirname(atomate2.dmax.__file__), 'templates')
print(f'Template dir: {template_dir}')
print(f'Exists: {os.path.exists(template_dir)}')
"
```

**Issue**: PSP Builder failures
```bash
# Check PSP is working
python -c "
from atomate2.dmax.generators.polymer_structure import build_amorphous_structure
print('PSP import OK')
"

# Test with simple example
python -c "
from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
maker = PSPStructureMaker(smiles='CC', length=2, num_molecules=5)
print('Maker created successfully')
"
```

### 3. Force Field Parameterization Issues

**Issue**: LigParGen failures
```bash
# Check network connectivity (LigParGen requires internet)
ping ligpargen.org

# Use local force field instead
# Set method="foyer" in ForceFieldMaker
```

**Issue**: Foyer parameterization fails
```bash
# Check force field availability
python -c "
from forcefield_utilities import FoyerFFs
print(FoyerFFs.get_available_force_fields())
"
```

## Performance Issues

### 1. Slow Simulations

**Issue**: LAMMPS runs too slowly
```bash
# Use optimized LAMMPS build
conda install -c conda-forge lammps=*=*openmpi*

# Check number of processors
export OMP_NUM_THREADS=4
mpirun -np 4 lmp_mpi < input.lammps
```

### 2. Memory Issues

**Issue**: Out of memory errors
```bash
# Reduce system size in PSPStructureMaker
# Reduce num_molecules or chain length

# Monitor memory usage
htop
# or
ps aux | grep python
```

## Debugging Tips

### 1. Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# For specific modules
logging.getLogger('atomate2.dmax').setLevel(logging.DEBUG)
```

### 2. Check Package Versions

```bash
# Create version check script
python -c "
import sys
import pkg_resources

packages = ['atomate2', 'jobflow', 'pymatgen', 'ase', 'mdanalysis', 'rdkit']
for pkg in packages:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f'{pkg}: {version}')
    except:
        print(f'{pkg}: NOT INSTALLED')
"
```

### 3. Test Individual Components

```bash
# Test structure generation
python -c "
from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
maker = PSPStructureMaker()
print('Structure maker: OK')
"

# Test force field
python -c "
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
maker = ForceFieldMaker()
print('Force field maker: OK')
"

# Test LAMMPS
python -c "
from atomate2.dmax.jobs.lammps_run import LammpsRunMaker
maker = LammpsRunMaker()
print('LAMMPS maker: OK')
"
```

## Getting Additional Help

### 1. Check Log Files

- JobFlow logs: Usually in `./logs/` directory
- LAMMPS logs: `log.lammps` in run directories
- PSP logs: Check PSP output directories

### 2. Community Resources

- [Atomate2 GitHub Issues](https://github.com/materialsproject/atomate2/issues)
- [JobFlow Documentation](https://materialsproject.github.io/jobflow/)
- [LAMMPS Documentation](https://docs.lammps.org/)

### 3. Create Minimal Reproducible Example

When reporting issues, include:

```python
# Minimal example that reproduces the problem
import atomate2.dmax
# ... minimal code that fails
```

- Python version: `python --version`
- Package versions: `pip list | grep -E "(atomate2|jobflow|pymatgen)"`
- Error traceback
- Operating system and environment details

### 4. Clean Installation

If all else fails, try a completely clean installation:

```bash
# Remove everything and start fresh
conda remove --name atomate2_dmax --all
rm -rf ~/atomate2_dmax_deps
rm -rf ~/atomate2_config

# Run fresh installation
./install_atomate2_dmax.sh
```

This should resolve most common issues. If problems persist, please create an issue on the GitHub repository with detailed error messages and system information.
