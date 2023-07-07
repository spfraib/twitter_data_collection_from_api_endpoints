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
	    --overlay /scratch/spf248/singularity/sam.ext3:ro \
	    /scratch/work/public/singularity/cuda11.6.124-cudnn8.4.0.27-devel-ubuntu20.04.4.sif\
	    /bin/bash -c "
source /ext3/env.sh
time python -u ./code/user_timeline_v1_endpoint.py
exit
" > ./log/user_timeline_v1_endpoint_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID} 2>&1
