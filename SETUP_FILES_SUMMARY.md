# Atomate2-DMAx Setup Files Summary

This document summarizes the setup and installation files created for the atomate2_dmax package.

## Files Created

### 1. Main Setup Documentation

#### `SETUP_GUIDE.md`
Comprehensive setup guide with detailed step-by-step instructions for:
- Environment creation and management
- Dependency installation
- Configuration setup
- Verification procedures
- Troubleshooting basic issues

#### `README_DMAX.md`
User-focused README specifically for DMAx functionality including:
- Quick start guide
- Feature overview
- Basic usage examples
- Core component descriptions
- Configuration instructions

#### `TROUBLESHOOTING.md`
Detailed troubleshooting guide covering:
- Common installation issues
- Configuration problems
- Runtime errors
- Performance optimization
- Debug strategies

### 2. Installation Scripts

#### `install_atomate2_dmax.sh`
**Main automated installation script** with features:
- Command-line argument parsing
- Colored output and logging
- Error handling and rollback
- Complete environment setup
- Configuration file generation
- Test script creation
- Post-installation instructions

Usage:
```bash
./install_atomate2_dmax.sh [OPTIONS]
```

Options:
- `-n, --name NAME`: Environment name (default: atomate2_dmax)
- `-d, --install-dir DIR`: Installation directory (default: ~/atomate2_dmax_deps)
- `-c, --config-dir DIR`: Configuration directory (default: ~/atomate2_config)
- `-p, --python VERSION`: Python version (default: 3.10)
- `-f, --force`: Force reinstallation
- `-h, --help`: Show help

#### `quick_setup.sh`
**Simplified setup script** for users who prefer conda environment files:
- Uses `environment.yml` for dependency management
- Minimal configuration
- Faster setup for experienced users

### 3. Dependency Management Files

#### `requirements.txt`
Python package requirements for pip installation including:
- Core atomate2 dependencies
- Molecular dynamics packages
- Development tools
- Comments explaining conda-forge dependencies

#### `environment.yml`
Complete conda environment specification with:
- Conda-forge packages (molecular tools, LAMMPS, etc.)
- Pip dependencies for Python-only packages
- Version constraints
- Multi-channel specification

### 4. Generated Configuration Templates

The installation scripts create configuration templates:

#### `jobflow.yaml` (created by installer)
JobFlow database configuration template with:
- MongoDB connection settings
- GridFS storage configuration
- Queue adapter settings (optional)
- Placeholder values for user customization

#### `atomate2.yaml` (created by installer)
Atomate2-DMAx specific settings with:
- LAMMPS command configuration
- Data storage preferences
- Computational parameters
- Force field settings

#### `atomate2_env.sh` (created by installer)
Environment activation script with:
- Environment variable exports
- Conda activation commands
- Path configurations
- User-friendly activation message

### 5. Test Scripts

#### `test_installation.py` (created by installer)
Comprehensive installation verification script that tests:
- Basic scientific packages (numpy, pandas, etc.)
- Molecular dynamics packages (ASE, MDAnalysis, etc.)
- Atomate2-dmax specific modules
- PolymerStructurePredictor (PSP) import
- Detailed success/failure reporting

#### `test_workflow.py` (created by installer)
Workflow creation verification script that tests:
- PSPStructureMaker instantiation
- ForceFieldMaker creation
- StructureEquilibrationMaker setup
- Basic workflow component functionality

### 6. Enhanced pyproject.toml

#### Updated Dependencies Section
Added `dmax` optional dependency group to `pyproject.toml`:
```toml
dmax = [
    "ase>=3.23.0",
    "mdanalysis>=2.8.0", 
    "jinja2>=3.0.0",
    "py3Dmol>=2.0.0",
    "scikit-learn>=1.0.0",
    # Notes about conda-forge packages
]
```

## Key Dependencies Identified

### Python Packages (pip installable)
- **Core**: jobflow, pymatgen, emmet-core, custodian, monty
- **Scientific**: numpy, scipy, pandas, matplotlib, scikit-learn
- **Utilities**: jinja2, py3Dmol, mp-api, ipykernel

### Conda-forge Packages (require conda)
- **Chemistry**: openbabel, rdkit, ambertools
- **Molecular Dynamics**: ase, mdanalysis, lammps
- **Force Fields**: mbuild, foyer, gmso, forcefield-utilities

### External Dependencies (manual installation)
- **PolymerStructurePredictor (PSP)**: https://github.com/rsilvabuarque/PSP_mod
- **BOSS Database**: Optional force field parameters
- **Atomate2-DMAx**: https://github.com/rsilvabuarque/atomate2_dmax.git (feature/dmax2-lammps branch)

## Installation Workflow

### Automated Installation Process
1. **Environment Setup**: Create conda environment with specified Python version
2. **Core Dependencies**: Install conda-forge packages (chemistry, MD tools)
3. **Python Packages**: Install pip packages (atomate2 ecosystem)
4. **External Tools**: Clone and install PSP and atomate2_dmax
5. **Configuration**: Generate config files and environment scripts
6. **Verification**: Create test scripts for validation
7. **Documentation**: Provide usage instructions and next steps

### Manual Installation Path
1. Follow SETUP_GUIDE.md step-by-step
2. Use requirements.txt and environment.yml as references
3. Configure databases and environment variables manually
4. Run test scripts for verification

## Usage Examples

### Full Automated Installation
```bash
# Standard installation
./install_atomate2_dmax.sh

# Custom installation
./install_atomate2_dmax.sh --name my_env --install-dir /custom/path --force
```

### Environment-based Installation
```bash
# Quick setup with conda environment file
conda env create -f environment.yml
./quick_setup.sh
```

### Manual Installation
```bash
# Follow SETUP_GUIDE.md
# Or use requirements.txt with pip
pip install -r requirements.txt
```

## Post-Installation Steps

1. **Activate Environment**:
   ```bash
   source ~/atomate2_config/atomate2_env.sh
   ```

2. **Configure Databases**:
   - Edit `~/atomate2_config/jobflow.yaml`
   - Edit `~/atomate2_config/atomate2.yaml`

3. **Verify Installation**:
   ```bash
   python ~/atomate2_dmax_deps/test_installation.py
   python ~/atomate2_dmax_deps/test_workflow.py
   ```

4. **Optional: Copy BOSS Database**:
   ```bash
   cp -r /path/to/BOSS ~/atomate2_dmax_deps/
   ```

## Maintenance and Updates

### Update Atomate2-DMAx
```bash
cd ~/atomate2_dmax_deps/atomate2_dmax
git pull origin feature/dmax2-lammps
pip install -e . --force-reinstall
```

### Update Dependencies
```bash
conda activate atomate2_dmax
conda update --all
pip install --upgrade pip
```

### Clean Reinstallation
```bash
./install_atomate2_dmax.sh --force
```

## Support and Troubleshooting

1. **First Steps**: Check TROUBLESHOOTING.md
2. **Test Scripts**: Run verification scripts
3. **Log Files**: Check installation and runtime logs
4. **Community**: Submit GitHub issues with detailed information

The setup system provides a comprehensive, automated solution for installing atomate2_dmax with all necessary dependencies while remaining flexible for different user needs and environments.
