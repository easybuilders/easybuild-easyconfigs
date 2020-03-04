#!/bin/bash
#SBATCH -J Relion
# Unset XXX...XXX values will be empty, and SBATCH without argument is ignored.
#SBATCH XXXaccountXXX
#SBATCH XXXtimelimitXXX
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX
#SBATCH XXXqueueXXX
#SBATCH XXXgpuspecXXX
#SBATCH XXXextrasbatchXXX

srun XXXcommandXXX
