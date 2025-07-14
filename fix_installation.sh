#!/bin/bash

# Fix script for atomate2_dmax installation issues
# Run this script to fix common installation problems

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Atomate2-DMAx Installation Fix Script${NC}"
echo "======================================"

# Check if environment exists
ENV_NAME="atomate2_dmax_new"  # Update to match your environment name
if ! conda env list | grep -q "$ENV_NAME"; then
    echo -e "${RED}Error: Environment $ENV_NAME not found!${NC}"
    echo "Please create the environment first or update ENV_NAME in this script."
    exit 1
fi

echo -e "${BLUE}Activating environment: $ENV_NAME${NC}"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate "$ENV_NAME"

# Fix 1: Install missing MDAnalysis
echo -e "${BLUE}Installing MDAnalysis...${NC}"
conda install -c conda-forge mdanalysis -y

# Fix 2: Create minimal atomate2.yaml configuration
CONFIG_DIR="${HOME}/atomate2_config"
echo -e "${BLUE}Creating minimal atomate2.yaml configuration...${NC}"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/atomate2.yaml" << 'EOF'
# Minimal Atomate2 configuration for DMAx
# Only includes settings recognized by base Atomate2Settings

# LAMMPS command (if supported by your atomate2 version)
LAMMPS_CMD: "lmp_serial"

# Uncomment if using VASP
# VASP_CMD: "vasp_std"

# Note: DMAx-specific settings are now handled in the DmaxSettings class
# located in atomate2.dmax.settings
EOF

# Fix 3: Update environment variables
echo -e "${BLUE}Updating environment variables...${NC}"
cat > "$CONFIG_DIR/atomate2_env_fixed.sh" << EOF
#!/bin/bash
# Fixed Atomate2-DMAx Environment Variables

export ATOMATE2_CONFIG_FILE="$CONFIG_DIR/atomate2.yaml"
export JOBFLOW_CONFIG_FILE="$CONFIG_DIR/jobflow.yaml"

# Optional: PSP and BOSS directories
export PSP_DIR="$HOME/atomate2_dmax_deps/PSP"
# export BOSS_DIR="$HOME/atomate2_dmax_deps/BOSS"  # Uncomment if BOSS is available

# Conda environment activation
conda activate $ENV_NAME

echo "Atomate2-DMAx environment activated (FIXED VERSION)!"
echo "Configuration directory: $CONFIG_DIR"
echo "Installation directory: $HOME/atomate2_dmax_deps"
EOF

chmod +x "$CONFIG_DIR/atomate2_env_fixed.sh"

# Fix 4: Test the installation
echo -e "${BLUE}Testing the fixed installation...${NC}"

# Create a simple test script
cat > "$HOME/atomate2_dmax_deps/test_installation_fixed.py" << 'EOF'
#!/usr/bin/env python3
"""Fixed test script for atomate2_dmax installation."""

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
    print("Testing FIXED atomate2_dmax installation...\n")
    
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
    ]
    md_success = all(test_import(pkg, desc) for pkg, desc in md_packages)
    
    # Test conda-forge packages (optional)
    print("\nOptional conda-forge packages:")
    optional_packages = [
        ('mbuild', ''),
        ('foyer', ''),
        ('gmso', ''),
        ('forcefield_utilities', ''),
    ]
    optional_success = all(test_import(pkg, desc) for pkg, desc in optional_packages)
    
    # Test PSP
    print("\nPolymerStructurePredictor:")
    psp_success = test_import('psp.AmorphousBuilder', '')
    
    # Test atomate2 base (should work now)
    print("\nAtomatе2 base:")
    try:
        import atomate2
        print("✓ atomate2 base import successful")
        atomate2_base_success = True
    except Exception as e:
        print(f"✗ atomate2 base import failed: {e}")
        atomate2_base_success = False
    
    # Test DMAx settings (new approach)
    print("\nDMAx specific modules:")
    try:
        from atomate2.dmax.settings import DMAX_SETTINGS
        print("✓ DMAx settings imported successfully")
        settings_success = True
    except Exception as e:
        print(f"✗ DMAx settings import failed: {e}")
        settings_success = False
    
    # Test DMAx workflows
    dmax_success = False
    try:
        from atomate2.dmax.flows.core import StructureEquilibrationFlow
        print("✓ DMAx workflows imported successfully")
        dmax_success = True
    except Exception as e:
        print(f"✗ DMAx workflows import failed: {e}")
    
    print("\n" + "="*50)
    print("INSTALLATION STATUS:")
    print(f"Basic packages: {'✓ PASS' if basic_success else '✗ FAIL'}")
    print(f"MD packages: {'✓ PASS' if md_success else '✗ FAIL'}")
    print(f"Optional packages: {'✓ PASS' if optional_success else '⚠ PARTIAL'}")
    print(f"PSP: {'✓ PASS' if psp_success else '✗ FAIL'}")
    print(f"Atomate2 base: {'✓ PASS' if atomate2_base_success else '✗ FAIL'}")
    print(f"DMAx settings: {'✓ PASS' if settings_success else '✗ FAIL'}")
    print(f"DMAx workflows: {'✓ PASS' if dmax_success else '✗ FAIL'}")
    
    if all([basic_success, md_success, psp_success, atomate2_base_success, settings_success, dmax_success]):
        print("\n🎉 Installation FIXED! All critical components working!")
        return 0
    elif atomate2_base_success and settings_success:
        print("\n⚠️  Core functionality working, some optional components may be missing")
        return 0
    else:
        print("\n❌ Installation still has issues. Check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "$HOME/atomate2_dmax_deps/test_installation_fixed.py"

echo -e "${GREEN}Fix script completed!${NC}"
echo
echo "Next steps:"
echo "1. Source the fixed environment:"
echo "   source $CONFIG_DIR/atomate2_env_fixed.sh"
echo
echo "2. Test the fixed installation:"
echo "   python $HOME/atomate2_dmax_deps/test_installation_fixed.py"
echo
echo "3. If tests pass, you can start using atomate2_dmax!"

# Run the test automatically
echo -e "${BLUE}Running test automatically...${NC}"
python "$HOME/atomate2_dmax_deps/test_installation_fixed.py"
