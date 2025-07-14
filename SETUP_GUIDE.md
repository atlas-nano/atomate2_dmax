# Atomate2-DMAx Package Setup Guide

This guide provides comprehensive instructions for setting up the `atomate2_dmax` package with all necessary dependencies for polymer molecular dynamics workflows.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Installation Instructions](#installation-instructions)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

- Access to a system with conda/mamba package manager
- Git access to clone repositories
- Python 3.10 or higher
- Sufficient disk space (~5-10 GB for all dependencies)

## Environment Setup

### Step 1: Create and Activate Conda Environment

```bash
# Load conda module (if on HPC system)
module load conda

# Remove any existing environment with the same name
conda remove --all -n atomate2_dmax

# Clean conda cache
conda clean --all

# Create new environment
conda create --name atomate2_dmax python=3.10

# Activate environment
conda activate atomate2_dmax
```

### Step 2: Install Core Dependencies

Install the fundamental packages required for molecular dynamics and force field generation:

```bash
# Install core molecular tools
conda install -y -c conda-forge openbabel
conda install -y -c conda-forge rdkit
conda install -y -c conda-forge ambertools
conda install -y -c conda-forge mdanalysis
conda install -y -c conda-forge ase

# Install additional molecular dynamics and analysis tools
conda install -y -c conda-forge mbuild
conda install -y -c conda-forge foyer
conda install -y -c conda-forge gmso
conda install -y -c conda-forge forcefield-utilities
conda install -y -c conda-forge lammps

# Install Python scientific computing stack
pip install ipykernel network py3Dmol jinja2 mp-api
pip install scipy scikit-learn matplotlib pandas numpy
```

### Step 3: Set Up PolymerStructurePredictor (PSP)

The DMAx workflow requires a modified version of PolymerStructurePredictor:

```bash
# Create directory for external dependencies
mkdir -p ${HOME}/atomate2_dmax_deps
cd ${HOME}/atomate2_dmax_deps

# Remove existing PSP installation if present
rm -rf PSP

# Clone the modified PSP repository
git clone https://github.com/rsilvabuarque/PSP_mod PSP
cd PSP

# Install PSP
python setup.py install

# Verify installation
pip show PolymerStructurePredictor
```

### Step 4: Install Atomate2-DMAx

```bash
# Navigate back to dependencies directory
cd ${HOME}/atomate2_dmax_deps

# Clone atomate2_dmax repository
git clone https://github.com/rsilvabuarque/atomate2_dmax.git
cd atomate2_dmax

# Checkout the correct branch
git checkout feature/dmax2-lammps
git pull origin feature/dmax2-lammps

# Install in development mode
pip install -e .
```

### Step 5: Set Up BOSS Force Field Database (Optional but Recommended)

If you need access to BOSS force field parameters:

```bash
# Copy BOSS database to your working directory
# Replace this path with the actual location of BOSS on your system
cp -r /global/cfs/cdirs/m4537/rsb/codes/BOSS/ ${HOME}/atomate2_dmax_deps/
```

### Step 6: Install Jupyter Kernel

Set up a Jupyter kernel for the environment:

```bash
python -m ipykernel install --user --name atomate2_dmax --display-name "atomate2_dmax"
```

## Configuration

### Step 1: Create Configuration Directory

```bash
# Create configuration directory
mkdir -p ${HOME}/atomate2_config
cd ${HOME}/atomate2_config
```

### Step 2: Set Up JobFlow Configuration

Create the `jobflow.yaml` file with your database credentials:

```bash
# Create jobflow configuration file
cat > jobflow.yaml << 'EOF'
# JobFlow database configuration
JOB_STORE:
  docs_store:
    type: MongoStore
    host: your_mongodb_host
    port: 27017
    database: your_database_name
    collection_name: jobs
    username: your_username
    password: your_password
  additional_stores:
    data:
      type: GridFSStore
      host: your_mongodb_host
      port: 27017
      database: your_database_name
      collection_name: outputs
      username: your_username
      password: your_password

# Queue adapter configuration (if using job submission system)
QUEUE_ADAPTER:
  _fw_name: CommonAdapter
  q_name: your_queue_name
  rocket_launch: rapidfire
  logdir: ./logs
EOF
```

### Step 3: Set Up Atomate2 Configuration

Create the `atomate2.yaml` file:

```bash
# Create atomate2 configuration file
cat > atomate2.yaml << 'EOF'
# Atomate2 configuration
LAMMPS_CMD: lmp_serial  # or your LAMMPS command
VASP_CMD: vasp_std     # if using VASP
LAMMPS_RUN_COMMAND: "lmp_serial"

# Data storage settings
STORE_VOLUMETRIC_DATA: true
STORE_TRAJECTORY: true

# Computational settings
LAMMPS_INCAR_UPDATES: {}
LAMMPS_KSPACING: 0.5
EOF
```

### Step 4: Set Environment Variables

Add the following to your shell configuration file (`.bashrc`, `.zshrc`, etc.):

```bash
# Add environment variables to your shell configuration
cat >> ~/.bashrc << 'EOF'

# Atomate2-DMAx Environment Variables
export ATOMATE2_CONFIG_FILE="${HOME}/atomate2_config/atomate2.yaml"
export JOBFLOW_CONFIG_FILE="${HOME}/atomate2_config/jobflow.yaml"

# Optional: BOSS force field database location
export BOSS_DIR="${HOME}/atomate2_dmax_deps/BOSS"

# Optional: PSP installation directory
export PSP_DIR="${HOME}/atomate2_dmax_deps/PSP"

EOF

# Reload shell configuration
source ~/.bashrc
```

## Verification

### Step 1: Test Basic Imports

Create a test script to verify the installation:

```python
# Create test_installation.py
cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""Test script for atomate2_dmax installation."""

import sys
import importlib

# Test basic scientific packages
packages_to_test = [
    'numpy',
    'pandas',
    'matplotlib',
    'scipy',
    'sklearn',
    'jobflow',
    'pymatgen',
    'ase',
    'mdanalysis',
    'rdkit',
]

# Test molecular dynamics packages
md_packages = [
    'mbuild',
    'foyer', 
    'gmso',
    'forcefield_utilities',
]

# Test atomate2 packages
atomate2_packages = [
    'atomate2',
    'atomate2.dmax',
    'atomate2.dmax.jobs',
    'atomate2.dmax.flows',
    'atomate2.dmax.generators',
]

def test_import(package_name):
    """Test if a package can be imported."""
    try:
        importlib.import_module(package_name)
        print(f"✓ {package_name}")
        return True
    except ImportError as e:
        print(f"✗ {package_name}: {e}")
        return False

print("Testing basic scientific packages:")
basic_success = all(test_import(pkg) for pkg in packages_to_test)

print("\nTesting molecular dynamics packages:")
md_success = all(test_import(pkg) for pkg in md_packages)

print("\nTesting atomate2-dmax packages:")
atomate2_success = all(test_import(pkg) for pkg in atomate2_packages)

print("\nTesting PSP (PolymerStructurePredictor):")
psp_success = test_import('psp.AmorphousBuilder')

if basic_success and md_success and atomate2_success and psp_success:
    print("\n🎉 All packages imported successfully!")
    sys.exit(0)
else:
    print("\n❌ Some packages failed to import. Check installation.")
    sys.exit(1)
EOF

# Run the test
python test_installation.py
```

### Step 2: Test Workflow Creation

```python
# Create test_workflow.py
cat > test_workflow.py << 'EOF'
#!/usr/bin/env python3
"""Test workflow creation with atomate2_dmax."""

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
from atomate2.dmax.flows.core import StructureEquilibrationMaker

def test_workflow_creation():
    """Test creating a simple workflow."""
    try:
        # Create structure generation job
        structure_maker = PSPStructureMaker(
            smiles="CC",
            length=5,
            num_molecules=10,
            density=0.8
        )
        
        # Create force field parameterization job
        ff_maker = ForceFieldMaker()
        
        # Create equilibration workflow
        equil_maker = StructureEquilibrationMaker()
        
        print("✓ Successfully created workflow makers")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create workflow: {e}")
        return False

if __name__ == "__main__":
    if test_workflow_creation():
        print("🎉 Workflow creation test passed!")
    else:
        print("❌ Workflow creation test failed!")
EOF

# Run the workflow test
python test_workflow.py
```

## Troubleshooting

### Common Issues and Solutions

1. **Import Error for PSP**: 
   - Ensure PSP is installed correctly: `pip show PolymerStructurePredictor`
   - Check that the PSP directory is in your Python path

2. **LAMMPS Not Found**:
   - Install LAMMPS: `conda install -c conda-forge lammps`
   - Set correct LAMMPS command in `atomate2.yaml`

3. **MongoDB Connection Issues**:
   - Verify database credentials in `jobflow.yaml`
   - Test connection manually with `pymongo`

4. **Environment Variable Issues**:
   - Verify variables are set: `echo $ATOMATE2_CONFIG_FILE`
   - Source your shell configuration: `source ~/.bashrc`

5. **BOSS Database Missing**:
   - This is optional but recommended for certain force fields
   - Copy from the provided path or contact maintainers

### Getting Help

For additional support:

1. Check the [atomate2 documentation](https://materialsproject.github.io/atomate2/)
2. Review the [JobFlow documentation](https://materialsproject.github.io/jobflow/)
3. Submit issues to the atomate2_dmax repository

## Summary

After following this guide, you should have:

- ✅ A working conda environment with all dependencies
- ✅ PolymerStructurePredictor (PSP) installed
- ✅ Atomate2-DMAx package installed
- ✅ Proper configuration files set up
- ✅ Environment variables configured
- ✅ Jupyter kernel for development
- ✅ Verified installation through testing

You're now ready to run polymer molecular dynamics workflows with atomate2_dmax!
