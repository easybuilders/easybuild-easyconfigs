"""
NOTE: GCCcore is a base (or core) compiler, which sits underneath "real" compilers like Intel, Clang, etc.
GCC is a bundle of GCCcore + binutils.

By building stuff with GCCcore , we can use those installations to resolve dependencies for stuff built with GCC, iccifort, foss, intel, etc.
So we don't need two or more (basically identical) installations.

We build stuff with GCCcore when performance is irrelevant and MPI or BLAS/LAPACK is not needed (like for CMake), but use GCC or iccifort when it does matter (like for scientific apps like DIAMOND)
"""
