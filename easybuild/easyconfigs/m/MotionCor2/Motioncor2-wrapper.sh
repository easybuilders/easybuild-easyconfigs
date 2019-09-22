#!/bin/bash

# Wrap around Motioncor2 to load the required toolchain so it can use the
# expected version of CUDA.

# Save path to the install tree.
mc_base=$EBROOTMOTIONCOR2

module unload CUDA > /dev/null 2>&1
module add CUDA/#CUDAVER#

exec $mc_base/bin/#MOTIONCOR2# "$@"
