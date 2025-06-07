#!/bin/bash -l

#SBATCH -C cpu
#SBATCH -t $${walltime}
#SBATCH -J $${job_name}
#SBATCH -o $${job_name}.o%j
#SBATCH -A m4537
#SBATCH -N $${nodes}
#SBATCH --ntasks-per-node $${ntasks_per_node}
#SBATCH -q $${queue}

input="-in in.lammps -log {{ job_name }}.log"

echo $SLURM_CPUS_PER_TASK
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

command="srun --cpu-bind=cores $LAMMPS_EXEC $input"
#command="shifter --image docker:nersc/lammps_all:24.08 lmp $input"


echo $command

$command
