#!/bin/bash

# Wrap around Gctf to load the required toolchain so it can use the
# expected version of CUDA.

# Save the path to the install tree
gctf_base=$EBROOTGCTF

module purge > /dev/null 2>&1
module CUDA/#CUDAVER#

exec $gctf_base/bin/#GCTF# "$@"
