#!/bin/bash -l
#SBATCH -C cpu
#SBATCH -t {{ slurm_time }}
#SBATCH -J {{ job_name }}
#SBATCH -o {{ job_name }}.o%j
#SBATCH -A m4537
#SBATCH -N 1
#SBATCH --ntasks-per-node={{ slurm_ntasks }}
#SBATCH --cpus-per-task=1
#SBATCH -q regular

input="-in in.lammps -log {{ job_name }}.log"

echo $SLURM_CPUS_PER_TASK
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

command="srun --cpu-bind=cores $LAMMPS_EXEC $input"

echo $command

$command
