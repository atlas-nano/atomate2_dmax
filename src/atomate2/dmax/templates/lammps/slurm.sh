#!/bin/bash -l

#SBATCH -C cpu
#SBATCH -t $${walltime}
#SBATCH -J $${job_name}
#SBATCH -o $${job_name}.o%j
#SBATCH -A $${account}
#SBATCH -N $${nodes}
#SBATCH --ntasks-per-node $${ntasks_per_node}
#SBATCH -q $${queue}

$${pre_rocket}
cd $${launch_dir}
$${rocket_launch}
$${post_rocket}

# CommonAdapter (PBS) completed writing Template
