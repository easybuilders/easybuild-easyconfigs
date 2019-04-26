#!/bin/bash
#SBATCH -A XXXextra1XXX
#SBATCH -J Relion
#SBATCH -t XXXextra2XXX
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX
#SBATCH --gres=gpu:XXXextra3XXX:XXXextra4XXX

srun XXXcommandXXX
