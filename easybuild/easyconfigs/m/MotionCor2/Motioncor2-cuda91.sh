#!/bin/bash

# Wrap around Motioncor2 to load the required toolchain so it can use the
# expected version of CUDA
# Save path to the install tree
mb_base=$EBROOTMOTIONCOR2

ml purge > /dev/null 2>&1
ml GCC/6.4.0-2.28
ml CUDA/9.1.85

# The #MOTIONCOR2# gets substituted with the correct name of the binary
exec $mb_base/bin/#MOTIONCOR2# "$@"
