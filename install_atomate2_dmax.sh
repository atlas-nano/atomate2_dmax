#!/bin/bash

# Atomate2-DMAx Automated Installation Script
# This script automates the installation of atomate2_dmax with all dependencies

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Default values
ENVIRONMENT_NAME="atomate2_dmax"
INSTALL_DIR="${HOME}/atomate2_dmax_deps"
CONFIG_DIR="${HOME}/atomate2_config"
PYTHON_VERSION="3.10"
FORCE_REINSTALL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            ENVIRONMENT_NAME="$2"
            shift 2
            ;;
        -d|--install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -c|--config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -p|--python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -f|--force)
            FORCE_REINSTALL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -n, --name NAME           Environment name (default: atomate2_dmax)"
            echo "  -d, --install-dir DIR     Installation directory (default: ~/atomate2_dmax_deps)"
            echo "  -c, --config-dir DIR      Configuration directory (default: ~/atomate2_config)"
            echo "  -p, --python VERSION      Python version (default: 3.10)"
            echo "  -f, --force               Force reinstallation"
            echo "  -h, --help                Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

log "Starting atomate2_dmax installation with the following settings:"
log "Environment name: $ENVIRONMENT_NAME"
log "Installation directory: $INSTALL_DIR"
log "Configuration directory: $CONFIG_DIR"
log "Python version: $PYTHON_VERSION"
log "Force reinstall: $FORCE_REINSTALL"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    error "conda command not found. Please install conda or load the conda module."
    exit 1
fi

# Step 1: Environment setup
log "Setting up conda environment..."

if conda env list | grep -q "$ENVIRONMENT_NAME"; then
    if [[ "$FORCE_REINSTALL" == true ]]; then
        warning "Removing existing environment: $ENVIRONMENT_NAME"
        conda remove --name "$ENVIRONMENT_NAME" --all -y
    else
        error "Environment $ENVIRONMENT_NAME already exists. Use -f to force reinstall."
        exit 1
    fi
fi

# Clean conda cache
log "Cleaning conda cache..."
conda clean --all -y

# Create environment
log "Creating conda environment: $ENVIRONMENT_NAME"
conda create --name "$ENVIRONMENT_NAME" python="$PYTHON_VERSION" -y

# Activate environment
log "Activating environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate "$ENVIRONMENT_NAME"

# Verify activation
if [[ "$CONDA_DEFAULT_ENV" != "$ENVIRONMENT_NAME" ]]; then
    error "Failed to activate environment: $ENVIRONMENT_NAME"
    exit 1
fi

success "Environment $ENVIRONMENT_NAME created and activated"

# Step 2: Install core dependencies
log "Installing core molecular dynamics dependencies..."

# Install from conda-forge
CONDA_PACKAGES=(
    "openbabel"
    "rdkit"
    "ambertools"
    "mdanalysis>=2.8.0"
    "ase>=3.23.0"
    "mbuild"
    "foyer"
    "gmso"
    "forcefield-utilities"
    "lammps"
    "matplotlib"
    "pandas"
    "numpy"
    "scipy"
    "jinja2"
)

for package in "${CONDA_PACKAGES[@]}"; do
    log "Installing $package..."
    conda install -y -c conda-forge "$package"
done

# Install pip packages
log "Installing additional Python packages..."
PIP_PACKAGES=(
    "ipykernel"
    "network"
    "py3Dmol"
    "mp-api"
    "scikit-learn"
    "pymongo<=4.10.1"
    "jobflow>=0.1.11"
    "pymatgen>=2024.11.13"
    "emmet-core>=0.84.3rc3"
    "custodian>=2024.4.18"
    "monty>=2024.12.10"
    "pydantic>=2.0.1"
    "pydantic-settings>=2.0.3"
    "PyYAML"
    "click"
)

for package in "${PIP_PACKAGES[@]}"; do
    log "Installing $package..."
    pip install "$package"
done

success "Core dependencies installed"

# Step 3: Set up directories
log "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Step 4: Install PolymerStructurePredictor (PSP)
log "Installing PolymerStructurePredictor (PSP)..."
cd "$INSTALL_DIR"

if [[ -d "PSP" ]]; then
    if [[ "$FORCE_REINSTALL" == true ]]; then
        warning "Removing existing PSP installation"
        rm -rf PSP
    else
        warning "PSP directory already exists. Skipping PSP installation."
    fi
fi

if [[ ! -d "PSP" ]]; then
    log "Cloning PSP repository..."
    git clone https://github.com/rsilvabuarque/PSP_mod PSP
    cd PSP
    log "Installing PSP..."
    python setup.py install
    
    # Verify PSP installation
    if pip show PolymerStructurePredictor &> /dev/null; then
        success "PSP installed successfully"
    else
        error "PSP installation failed"
        exit 1
    fi
else
    log "PSP already installed, skipping"
fi

# Step 5: Install atomate2_dmax
log "Installing atomate2_dmax..."
cd "$INSTALL_DIR"

if [[ -d "atomate2_dmax" ]]; then
    if [[ "$FORCE_REINSTALL" == true ]]; then
        warning "Removing existing atomate2_dmax installation"
        rm -rf atomate2_dmax
    else
        warning "atomate2_dmax directory already exists. Updating..."
        cd atomate2_dmax
        git checkout feature/dmax2-lammps
        git pull origin feature/dmax2-lammps
    fi
fi

if [[ ! -d "atomate2_dmax" ]]; then
    log "Cloning atomate2_dmax repository..."
    git clone https://github.com/rsilvabuarque/atomate2_dmax.git
    cd atomate2_dmax
    git checkout feature/dmax2-lammps
    git pull origin feature/dmax2-lammps
else
    cd atomate2_dmax
fi

log "Installing atomate2_dmax in development mode..."
pip install -e .

success "atomate2_dmax installed successfully"

# Step 6: Set up Jupyter kernel
log "Setting up Jupyter kernel..."
python -m ipykernel install --user --name "$ENVIRONMENT_NAME" --display-name "$ENVIRONMENT_NAME"
success "Jupyter kernel installed"

# Step 7: Create configuration files
log "Creating configuration files..."

# Create jobflow.yaml template
cat > "$CONFIG_DIR/jobflow.yaml" << 'EOF'
# JobFlow database configuration
# Replace the placeholder values with your actual database credentials

JOB_STORE:
  docs_store:
    type: MongoStore
    host: "your_mongodb_host"  # e.g., "localhost" or "mongodb.example.com"
    port: 27017
    database: "your_database_name"  # e.g., "atomate2_jobs"
    collection_name: "jobs"
    username: "your_username"
    password: "your_password"
    
  additional_stores:
    data:
      type: GridFSStore
      host: "your_mongodb_host"
      port: 27017
      database: "your_database_name"
      collection_name: "outputs"
      username: "your_username"
      password: "your_password"

# Uncomment and configure if using a job submission system
# QUEUE_ADAPTER:
#   _fw_name: CommonAdapter
#   q_name: "your_queue_name"
#   rocket_launch: rapidfire
#   logdir: "./logs"
EOF

# Create atomate2.yaml template
cat > "$CONFIG_DIR/atomate2.yaml" << 'EOF'
# Atomate2-DMAx configuration
# Only include settings that are recognized by Atomate2Settings

# LAMMPS settings (if supported by your atomate2 version)
LAMMPS_CMD: "lmp_serial"  # or "lmp_mpi", "lammps", etc.

# Optional: VASP settings (if using VASP)
# VASP_CMD: "vasp_std"

# Note: The following settings may not be recognized by base atomate2
# and should be handled in your workflow code or custom settings:
# - LAMMPS_RUN_COMMAND
# - STORE_VOLUMETRIC_DATA  
# - STORE_TRAJECTORY
# - LAMMPS_INCAR_UPDATES
# - LAMMPS_KSPACING
# - DEFAULT_FF_METHOD
# - DEFAULT_FF_NAME

# If you need these settings, consider creating a custom settings class
# or handling them directly in your workflow makers.
EOF

success "Configuration files created in $CONFIG_DIR"

# Step 8: Set up environment variables
log "Setting up environment variables..."

ENV_VARS_FILE="$CONFIG_DIR/atomate2_env.sh"
cat > "$ENV_VARS_FILE" << EOF
#!/bin/bash
# Atomate2-DMAx Environment Variables
# Source this file to set up your environment: source $ENV_VARS_FILE

export ATOMATE2_CONFIG_FILE="$CONFIG_DIR/atomate2.yaml"
export JOBFLOW_CONFIG_FILE="$CONFIG_DIR/jobflow.yaml"

# Optional: PSP and BOSS directories
export PSP_DIR="$INSTALL_DIR/PSP"
# export BOSS_DIR="$INSTALL_DIR/BOSS"  # Uncomment if BOSS is available

# Conda environment activation
conda activate $ENVIRONMENT_NAME

echo "Atomate2-DMAx environment activated!"
echo "Configuration directory: $CONFIG_DIR"
echo "Installation directory: $INSTALL_DIR"
EOF

chmod +x "$ENV_VARS_FILE"

# Step 9: Create test scripts
log "Creating test scripts..."

# Create installation test script
cat > "$INSTALL_DIR/test_installation.py" << 'EOF'
#!/usr/bin/env python3
"""Test script for atomate2_dmax installation."""

import sys
import importlib

def test_import(package_name, description=""):
    """Test if a package can be imported."""
    try:
        importlib.import_module(package_name)
        print(f"✓ {package_name} {description}")
        return True
    except ImportError as e:
        print(f"✗ {package_name} {description}: {e}")
        return False

def main():
    print("Testing atomate2_dmax installation...\n")
    
    # Test basic scientific packages
    print("Basic scientific packages:")
    basic_packages = [
        ('numpy', ''),
        ('pandas', ''),
        ('matplotlib', ''),
        ('scipy', ''),
        ('sklearn', '(scikit-learn)'),
        ('jobflow', ''),
        ('pymatgen', ''),
    ]
    basic_success = all(test_import(pkg, desc) for pkg, desc in basic_packages)
    
    # Test molecular dynamics packages
    print("\nMolecular dynamics packages:")
    md_packages = [
        ('ase', ''),
        ('mdanalysis', ''),
        ('rdkit', ''),
        ('mbuild', ''),
        ('foyer', ''),
        ('gmso', ''),
        ('forcefield_utilities', ''),
    ]
    md_success = all(test_import(pkg, desc) for pkg, desc in md_packages)
    
    # Test atomate2 packages
    print("\nAtomatе2-dmax packages:")
    atomate2_packages = [
        ('atomate2', ''),
        ('atomate2.dmax', ''),
        ('atomate2.dmax.jobs', ''),
        ('atomate2.dmax.flows', ''),
        ('atomate2.dmax.generators', ''),
    ]
    atomate2_success = all(test_import(pkg, desc) for pkg, desc in atomate2_packages)
    
    # Test PSP
    print("\nPolymerStructurePredictor:")
    psp_success = test_import('psp.AmorphousBuilder', '')
    
    print("\n" + "="*50)
    if all([basic_success, md_success, atomate2_success, psp_success]):
        print("🎉 All packages imported successfully!")
        print("Your atomate2_dmax installation is ready to use!")
        return 0
    else:
        print("❌ Some packages failed to import.")
        print("Please check the installation guide for troubleshooting.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "$INSTALL_DIR/test_installation.py"

# Create workflow test script
cat > "$INSTALL_DIR/test_workflow.py" << 'EOF'
#!/usr/bin/env python3
"""Test workflow creation with atomate2_dmax."""

def test_workflow_creation():
    """Test creating a simple workflow."""
    try:
        from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
        from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker
        from atomate2.dmax.flows.core import StructureEquilibrationMaker
        
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
        print("✓ PSPStructureMaker: OK")
        print("✓ ForceFieldMaker: OK") 
        print("✓ StructureEquilibrationMaker: OK")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create workflow: {e}")
        return False

def main():
    print("Testing atomate2_dmax workflow creation...\n")
    
    if test_workflow_creation():
        print("\n🎉 Workflow creation test passed!")
        print("You can now create and run atomate2_dmax workflows!")
        return 0
    else:
        print("\n❌ Workflow creation test failed!")
        print("Check the installation and configuration.")
        return 1

if __name__ == "__main__":
    exit(main())
EOF

chmod +x "$INSTALL_DIR/test_workflow.py"

# Step 10: Final instructions
success "Installation completed successfully!"

echo
echo "="*60
echo -e "${GREEN}Atomate2-DMAx Installation Complete!${NC}"
echo "="*60
echo
echo "To get started:"
echo "1. Activate your environment:"
echo "   source $ENV_VARS_FILE"
echo
echo "2. Configure your database settings:"
echo "   Edit $CONFIG_DIR/jobflow.yaml"
echo "   Edit $CONFIG_DIR/atomate2.yaml"
echo
echo "3. Test your installation:"
echo "   python $INSTALL_DIR/test_installation.py"
echo "   python $INSTALL_DIR/test_workflow.py"
echo
echo "4. (Optional) Copy BOSS force field database if available:"
echo "   cp -r /path/to/BOSS $INSTALL_DIR/"
echo
echo "Configuration files:"
echo "  - JobFlow config: $CONFIG_DIR/jobflow.yaml"
echo "  - Atomate2 config: $CONFIG_DIR/atomate2.yaml"
echo "  - Environment setup: $ENV_VARS_FILE"
echo
echo "Installation directory: $INSTALL_DIR"
echo "Environment name: $ENVIRONMENT_NAME"
echo
echo "For troubleshooting, see SETUP_GUIDE.md"
echo "="*60

log "Installation script completed successfully!"
