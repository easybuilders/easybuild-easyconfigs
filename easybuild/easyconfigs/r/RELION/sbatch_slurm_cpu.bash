#!/bin/bash
#SBATCH -J XXXnameXXX
# Unset XXX...XXX values will be empty, and SBATCH without argument is ignored.
#SBATCH -t XXXextra1XXX:00:00
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX
#SBATCH -A XXXextra2XXX
#SBATCH XXXqueueXXX
#SBATCH XXXextra3XXX

srun XXXcommandXXX
