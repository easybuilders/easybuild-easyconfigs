#//////////////////////////////////////////////////////////////////////////////
#   -- MAGMA (version 1.6.1) --
#      Univ. of Tennessee, Knoxville
#      Univ. of California, Berkeley
#      Univ. of Colorado, Denver
#      @date January 2015
#
#  make.inc updated by @twrobinson and @gppezzi for compilation on XC30 (Piz Daint)
#
#//////////////////////////////////////////////////////////////////////////////


# GPU_TARGET contains one or more of Tesla, Fermi, or Kepler,
# to specify for which GPUs you want to compile MAGMA:
#     Tesla  - NVIDIA compute capability 1.x cards (no longer supported in CUDA 6.5)
#     Fermi  - NVIDIA compute capability 2.x cards
#     Kepler - NVIDIA compute capability 3.x cards
# The default is "Fermi Kepler".
# See http://developer.nvidia.com/cuda-gpus
#
GPU_TARGET = Fermi Kepler

CXX      := $(CXX)
CC       := $(CC)
NVCC     := nvcc
FORT     := $(F90)

ARCH      = ar
ARCHFLAGS = cr
RANLIB    = ranlib

# Use -fPIC to make shared (.so) and static (.a) library;
# can be commented out if making only static library.
FPIC      = -fPIC

CFLAGS    += -DADD_ -DMAGMA_SETAFFINITY
CXXFLAGS  += -DADD_ -DMAGMA_SETAFFINITY
FFLAGS    += -DADD_ -Wall -Wno-unused-dummy-argument
F90FLAGS  += -DADD_ -Wall -Wno-unused-dummy-argument -x f95-cpp-input
NVCCFLAGS += -O3 -DADD_ -Xcompiler "-fno-strict-aliasing $(FPIC)"

# gcc with OpenBLAS (includes LAPACK)
LIB       = -lcublas $(LIBS)

# define library directories preferably in your environment, or here.
CUDADIR   = $(EBROOTCUDA)

LIBDIR    = -L$(CUDADIR)/lib64 

INC       = -I$(CUDADIR)/include
prefix    = $(EBINSTALLPREFIX)
