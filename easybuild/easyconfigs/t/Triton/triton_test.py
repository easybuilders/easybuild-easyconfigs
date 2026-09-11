"""Basic test the Triton installation works"""

import sys
import triton
from triton.backends.compiler import GPUTarget


@triton.jit
def kernel(_a, _b):
    pass


src = triton.compiler.ASTSource(
    fn=kernel,
    signature={"_a": "i32", "_b": "i32"},
)

cuda_cc = sys.argv[1].split(',')[-1]
cuda_cc_digits = [d for d in cuda_cc if d.isdigit()]  # Strip dots and suffixes, e.g. from 9.0a
target = GPUTarget("cuda", int(''.join(cuda_cc_digits)), 32)
output = triton.compile(src, target=target)
print(output)
