#!/bin/bash

# Wrap around Motioncor2 to load the required toolchain so it can use the
# expected version of CUDA.

# Save path to the install tree.
mc_base=$EBROOTMOTIONCOR2

ml purge > /dev/null 2>&1
ml CUDA/#CUDAVER#

exec $mc_base/bin/#MOTIONCOR2# "$@"
