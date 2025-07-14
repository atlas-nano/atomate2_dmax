#!/bin/bash

# Quick setup script for atomate2_dmax using conda environment file

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Quick Setup for atomate2_dmax${NC}"
echo "=================================="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda not found. Please install conda or load the conda module.${NC}"
    exit 1
fi

# Create environment from file
echo -e "${BLUE}Creating conda environment from environment.yml...${NC}"
conda env create -f environment.yml

# Activate environment
echo -e "${BLUE}Activating environment...${NC}"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate atomate2_dmax

# Ensure MDAnalysis is installed (sometimes conda-forge has issues)
echo -e "${BLUE}Ensuring MDAnalysis is installed...${NC}"
conda install -c conda-forge mdanalysis -y

# Install PSP
echo -e "${BLUE}Installing PolymerStructurePredictor (PSP)...${NC}"
INSTALL_DIR="${HOME}/atomate2_dmax_deps"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ ! -d "PSP" ]; then
    git clone https://github.com/rsilvabuarque/PSP_mod PSP
    cd PSP
    python setup.py install
    echo -e "${GREEN}PSP installed successfully${NC}"
else
    echo "PSP already exists, skipping..."
fi

# Install atomate2_dmax
echo -e "${BLUE}Installing atomate2_dmax...${NC}"
cd "$INSTALL_DIR"

if [ ! -d "atomate2_dmax" ]; then
    git clone https://github.com/rsilvabuarque/atomate2_dmax.git
    cd atomate2_dmax
    git checkout feature/dmax2-lammps
    pip install -e .
    echo -e "${GREEN}atomate2_dmax installed successfully${NC}"
else
    echo "atomate2_dmax already exists, updating..."
    cd atomate2_dmax
    git checkout feature/dmax2-lammps
    git pull origin feature/dmax2-lammps
    pip install -e .
fi

# Setup Jupyter kernel
echo -e "${BLUE}Setting up Jupyter kernel...${NC}"
python -m ipykernel install --user --name atomate2_dmax --display-name "atomate2_dmax"

# Create config directory
CONFIG_DIR="${HOME}/atomate2_config"
mkdir -p "$CONFIG_DIR"

echo
echo -e "${GREEN}Quick setup completed!${NC}"
echo
echo "Next steps:"
echo "1. Activate environment: conda activate atomate2_dmax"
echo "2. Configure databases in: $CONFIG_DIR/"
echo "3. Set environment variables:"
echo "   export ATOMATE2_CONFIG_FILE=\"$CONFIG_DIR/atomate2.yaml\""
echo "   export JOBFLOW_CONFIG_FILE=\"$CONFIG_DIR/jobflow.yaml\""
echo
echo "For detailed setup, use the full installation script: ./install_atomate2_dmax.sh"
