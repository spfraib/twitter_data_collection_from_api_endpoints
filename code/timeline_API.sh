#!/bin/bash

#SBATCH --job-name=user_timeline
#SBATCH --nodes=1
#SBATCH --mem=10GB
#SBATCH --time=168:00:00
#SBATCH --cpus-per-task=1
##SBATCH --gres=gpu:1
#SBATCH --output=slurm_user_timeline_%j.out
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-user=samuel.fraiberger@nyu.edu

module purge
cd /scratch/spf248/twitter_data_collection
singularity exec --nv \
            --overlay /scratch/spf248/singularity/pytorch1.7.0-cuda11.0.ext3:ro \
            /scratch/work/public/singularity/cuda11.0-cudnn8-devel-ubuntu18.04.sif \
            /bin/bash -c "
source /ext3/env.sh
time python -u ./code/retweeters_API.py
exit
" > ./log/timeline_API/timeline_API_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID} 2>&1
