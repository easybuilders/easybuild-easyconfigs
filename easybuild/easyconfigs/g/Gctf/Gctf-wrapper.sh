#!/bin/bash

# Wrap around Gctf to load the requrired toolchain so it can use the
# expected version of CUDA

# Save the path to the install tree
gctf_base=$EBROOTGCTF

ml purge > /dev/null 2>&1
ml GCC/5.4.0-2.26
ml CUDA/8.0.61_375.26

exec $gctf_base/bin/Gctf-v1.06_sm_30_cu8.0_x86_64 "$@"
