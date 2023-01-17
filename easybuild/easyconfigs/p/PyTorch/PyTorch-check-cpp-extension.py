#!/usr/bin/env python

# Verify that PyTorch can JIT compile C++ extensions
# This requires at least Ninja and a working C++ compiler, preferably GCC
#
# Heavily based on the PyTorch tutorial for C++ extensions
# Author: Alexander Grund (TU Dresden)

from torch.utils.cpp_extension import load_inline

cpp_source = "torch::Tensor test_func(torch::Tensor x) { return x; }"

module = load_inline(name='inline_extension',
                     cpp_sources=cpp_source,
                     functions=['test_func'])
assert module
