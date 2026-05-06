#!/usr/bin/env python

# Verify that PyTorch can load CUTLASS, required for the CUTLASS inductor backend
# Author: Alexander Grund (TU Dresden)

import os
import tempfile
from torch._inductor.codegen.cuda.cutlass_utils import try_import_cutlass, config

# Isolate from default path used
os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(suffix='inductor_cache')
# Use empty working directory
os.chdir(tempfile.mkdtemp(suffix='cwd'))


if try_import_cutlass():
    print(f"CUTLASS is set up using {config.cuda.cutlass_dir}")
else:
    raise RuntimeError("CUTLASS is NOT working")
