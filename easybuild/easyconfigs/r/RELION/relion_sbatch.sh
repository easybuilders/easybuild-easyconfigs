#!/bin/bash
#SBATCH -J Relion
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX
#SBATCH XXXqosXXX
#SBATCH -t XXXextra1XXX
#SBATCH -A XXXextra2XXX
#SBATCH XXXextra3XXX

srun XXXcommandXXX
