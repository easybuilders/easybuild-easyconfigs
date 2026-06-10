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
target = GPUTarget("cuda", int(cuda_cc.replace('.', '')), 32)
output = triton.compile(src, target=target)
print(output)
