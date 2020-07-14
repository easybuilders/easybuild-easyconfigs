#!/bin/bash
#PBS -V
#PBS -N XXXnameXXX
#PBS -l nodes=XXXmpinodesXXX:ppn=XXXthreadsXXX:gpus=XXXextra2XXX
#PBS -l walltime=XXXextra1XXX:00:00
#PBS -q XXXqueueXXX
#PBS -e XXXerrfileXXX
#PBS -o XXXoutfileXXX

cd $PBS_O_WORKDIR

mpirun -n XXXmpinodesXXX XXXcommandXXX
