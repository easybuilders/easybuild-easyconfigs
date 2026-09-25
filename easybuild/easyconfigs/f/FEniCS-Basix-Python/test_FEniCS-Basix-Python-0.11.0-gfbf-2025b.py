#!/usr/bin/env python3

import basix

element = basix.create_element(basix.ElementFamily.P, basix.CellType.triangle, 1)
assert element.dim == 3, f"Expected 3 DOFs, got {element.dim}"
