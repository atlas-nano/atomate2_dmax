#!/bin/bash -l
#SBATCH --image docker:nersc/lammps_all:24.08
#SBATCH -C gpu
#SBATCH -t {{ slurm_time }}
#SBATCH -J {{ job_name }}
#SBATCH -o {{ job_name }}.o%j
#SBATCH -A m4537_g
#SBATCH -N 1
#SBATCH -c 32
#SBATCH --ntasks-per-node={{ slurm_ntasks }}
#SBATCH --gpus-per-task=1
#SBATCH --gpu-bind=none
#SBATCH -q premium

exe=lmp
input="-k on g 4 -sf kk -pk kokkos newton on neigh half -in in.lammps -log {{ job_name }}.log"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

command="srun --cpu-bind=cores --gpu-bind=none --module mpich,gpu shifter lmp $input"

echo $command

$command
