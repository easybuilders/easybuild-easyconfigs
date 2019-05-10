#!/bin/bash

# Wrap around Gctf to load the required version of CUDA.

# Save the path to the install tree
gctf_base=$EBROOTGCTF

module unload CUDA > /dev/null 2>&1
module CUDA/#CUDAVER#

exec $gctf_base/bin/#GCTF# "$@"
