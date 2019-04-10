#!/bin/bash
#SBATCH -A XXXextra1XXX
#SBATCH -J Relion
#SBATCH -t XXXextra2XXX
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX

srun XXXcommandXXX
