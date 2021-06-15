# This is the config file for specifying tables necessary to configure XALT:

# The patterns listed here are the hosts that can track executable with XALT.
# Typical usage is that compute nodes track executable with XALT while login
# nodes do not.

import sys

# Note that linking an executable is everywhere and is independent of
# hostname_patterns

hostname_patterns = [
    ['KEEP', '.*']                              # capture executables on all nodes!
    #['KEEP', '^[a-z]{3}[0-9][0-9][0-9]\..*']   # only capture compute nodes
    ]


#------------------------------------------------------------
# This "table" is use to filter executables by their path
# The value on the left is either KEEP or SKIP.  If the value
# is KEEP then if the path matches the regular expression then
# the executable is acceptable as far as the path test goes.
# If the value on the left is SKIP then if the path matches
# the regular expression then executable is not acceptable so
# no XALT tracking is done for that path.

# This "table" is used to generate a flex routine that processes
# the paths. So the regular express must follow flex rules.
# In particular, in order to match the pattern must match the whole path
# No partial matches allowed.  Also do not use $ to match the
# end of the string.  Finally slash is a special character and must
# be quoted with a backslash.

# The path are conceptionally matched from the first regular
# expression to the last.  Once a match is found no other later
# matches are checked. The upshot of this is that if you want to
# track say /usr/bin/ddt, but ignore everything in /usr, then keep
# /usr/bin/ddt first and skip /usr/.* after.

# If a path does not match any patterns it is marked as KEEP.

# Programs like R, MATLAB and python* are marked as PKGS.  These programs
# can optionally track the internal "import" that are used.

path_patterns = [
    # Track packages
    ['PKGS',  r'.*\/R'],
    ['PKGS',  r'.*\/MATLAB'],
    ['PKGS',  r'.*\/python[0-9.]*'],

    ['KEEP',  r'.*\/bin\/cp'],
    ['KEEP',  r'.*\/bin\/mv'],
    ['KEEP',  r'.*\/bin\/gawk'],
    ['KEEP',  r'.*\/bin\/sed'],
    ['KEEP',  r'.*\/bin\/perl'],
    ['KEEP',  r'.*\/bin\/grep'],
    ['KEEP',  r'.*\/bin\/bzip2'],
    ['KEEP',  r'.*\/bin\/gzip'],
    ['KEEP',  r'.*\/bin\/tar'],

    ['SKIP',  r'^\/usr\/.*'],
    ['SKIP',  r'^\/sbin\/.*'],
    ['SKIP',  r'^\/bin\/.*'],
    ['SKIP',  r'^\/etc\/.*'],
    ['SKIP',  r'^\/root\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/gentoo\/2020\/usr\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/gentoo\/2020\/sbin\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/gentoo\/2020\/bin\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/gentoo\/2020\/etc\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/gentoo\/2020\/root\/.*'],
    ['SKIP',  r'\/cvmfs\/soft.computecanada.ca\/nix\/store\/.*'],

    # General executables to ignore
    ['SKIP',  r'.*\/git'],
    ['SKIP',  r'.*\/lua'],
    ['SKIP',  r'.*\/mpiCC'],
    ['SKIP',  r'.*\/mpicc'],
    ['SKIP',  r'.*\/mpicxx'],
    ['SKIP',  r'.*\/mpif77'],
    ['SKIP',  r'.*\/mpif90'],
    ['SKIP',  r'.*\/mpifort'],
    ['SKIP',  r'.*\/mpifc'],
    ['SKIP',  r'.*\/mpigcc'],
    ['SKIP',  r'.*\/mpigxx'],
    ['SKIP',  r'.*\/mpiicc'],
    ['SKIP',  r'.*\/mpiicpc'],
    ['SKIP',  r'.*\/mpiifort'],
    ['SKIP',  r'.*\/mpiexec.hydra'],
    ['SKIP',  r'.*\/hydra_pmi_proxy'],
    ['SKIP',  r'.*\/ompi_info'],
    ['SKIP',  r'.*\/opal_wrapper'],
    ['SKIP',  r'.*\/orterun'],
    ['SKIP',  r'.*\/vtwrapper'],
    ['SKIP',  r'.*\/conftest'],
    ['SKIP',  r'.*\/CMakeTmp\/cmTryCompileExec[0-9][0-9]*'],
    ['SKIP',  r'.*\/CMakeTmp\/cmTC_[a-f0-9][a-f0-9]*'],
  ]

# Remove tracking for these directories in these environments
# for dir in ['usr', 'sbin', 'bin', 'etc', 'root']:
#     for path in ['\/cvmfs\/soft.computecanada.ca\/gentoo\/2020', '\/cvmfs\/soft.computecanada.ca\/nix\/var\/nix\/profiles\/16.09']:
#         path_patterns.append(['SKIP', fr'{path}\/{dir}\/.*'])

#------------------------------------------------------------
# XALT samples almost all  executions (both MPI and scalar)
# based on this table below.  Note that an MPI execution is where
# the number of tasks is greater than 1.  There is no check to
# see if there are MPI libraries in the executable.  Note that
# the number of tasks are MPI tasks not threads.

# Any time there are a number of short rapid executions these
# have to be sampled. However, there are MPI executions with large
# number of tasks that are always recorded.  This is to allow the
# tracking of long running MPI tasks that never produce an end
# record. By default MPI_ALWAYS_RECORD = 1.  Namely that all MPI
# tasks are recorded.

MPI_ALWAYS_RECORD = 128

#------------------------------------------------------------
# The array of array used by interval_array has the following
# structure:
#
#   interval_array = [
#                     [ t_0,     probability_0],
#                     [ t_1,     probability_1],
#                     ...
#                     [ t_n,     probability_n],
#                     [ 1.0e308, 1.0],
#
#
# The first number is the left edge of the time range.  The
# second number is the probability of being sampled. Where a
# probability of 1.0 means a 100% chance of being recorded and a
# value of 0.01 means a 1% chance of being recorded.
#
# So a table that looks like this:
#     interval_array = [
#                       [ 0.0,                0.0001 ],
#                       [ 300.0,              0.01   ],
#                       [ 600.0,              1.0    ],
#                       [ sys.float_info.max, 1.0    ]
#     ]
#
# would say that program with execution time that is between
# 0.0 and 300.0 seconds has a 0.01% chance of being recorded.
# Execution times between 300.0 and 600.0 seconds have a 1%
# chance of being recorded and and programs that take longer
# than 600 seconds will always be recorded.
#
# The absolute minimum table would look like:
#
#     interval_array = [
#                       [ 0.0,                1.0 ],
#                       [ sys.float_info.max, 1.0 ]
#     ]
#
# which says to record every scalar (non-mpi) program no matter
# the execution time.
#
# Note that scalar execution only uses this table IFF
# $XALT_SAMPLING equals yes


interval_array = [
    [    0.0,              0.0001 ],
    [ 1800.0,              0.01   ],
    [ 7200.0,              1.0    ],
    [ sys.float_info.max,  1.0    ]
]

#------------------------------------------------------------
# Sites can also define a different sampling specification
# for mpi programs different from interval_array.  If no
# mpi_interval_array is given then the interval_array is used
# for both scalar and mpi programs.

mpi_interval_array = [
    [    0.0,              0.0001 ],
    [  900.0,              0.01   ],
    [ 1800.0,              1.0    ],
    [ sys.float_info.max,  1.0    ]
]

#------------------------------------------------------------
# XALT filter environment variables.  Those variables
# which pass through the filter are save in an SQL table that is
# searchable via sql commands.  The environment variables are passed
# to this filter routine as:
#
#      env_key=env_value
#
# So the regular expression patterns must match the whole string.


# The value on the left is either KEEP or SKIP.  If the value
# is KEEP then if the environment string matches the regular
# expression then the variable is stored. If the value on the left
# is SKIP then if the variable matches it is not stored.

# Order of the list matters.  The first match is used even if a
# later pattern would also match.  The upshot is that special pattern
# matches should appear first and general ones later.

# If the environment string does not match any pattern then it is
# marked as SKIP.


env_patterns = [
    # These are monitored

    # These are not monitored
    [ 'SKIP', r'^CC_CLUSTER=.*'],
    [ 'SKIP', r'^HOSTNAME=.*'],
    [ 'SKIP', r'^LD=.*'],
    [ 'SKIP', r'^LOADEDMODULES=.*'],
    [ 'SKIP', r'^MKL.*'],
    [ 'SKIP', r'^OFFLOAD.*'],
    [ 'SKIP', r'^OMP.*'],
    [ 'SKIP', r'^PATH=.*'],
    [ 'SKIP', r'^PYTHON.*'],
    [ 'SKIP', r'^R_.*'],
    [ 'SKIP', r'^LAUNCHER_TSK_ID=.*'],
    [ 'SKIP', r'^PYLAUNCHER_ENABLED=.*'],
    [ 'SKIP', r'^_LMFILES_=.*'],
    [ 'SKIP', r'^MKLROOT=.*' ],
    [ 'SKIP', r'^MKL_DIR=.*' ],
    [ 'SKIP', r'^MKL_INCLUDE=.*' ],
    [ 'SKIP', r'^MKL_LIB=.*' ],
    [ 'SKIP', r'^MPICH_HOME=.*' ],
    [ 'SKIP', r'^MV2_COMM_WORLD=.*'],
    [ 'SKIP', r'^MV2_CPU_BINDING_POLICY=.*' ],
    [ 'SKIP', r'^MV2_DEFAULT_TIME_OUT=.*' ],
    [ 'SKIP', r'^MV2_HOMOGENEOUS_CLUSTER=.*' ],
    [ 'SKIP', r'^MV2_HYBRID_BINDING_POLICY=.*' ],
    [ 'SKIP', r'^MV2_IBA_HCA=.*' ],
    [ 'SKIP', r'^MV2_NODE_ID=.*' ],
    [ 'SKIP', r'^MV2_NUM_NODES_IN_JOB=.*' ],
    [ 'SKIP', r'^MV2_THREADS_PER_PROCESS=.*' ],
    [ 'SKIP', r'^MV2_USE_HUGEPAGES=.*' ],
    [ 'SKIP', r'^MV2_USE_OLD_BCAST=.*' ],
    [ 'SKIP', r'^MV2_USE_RING_STARTUP=.*' ],
    [ 'SKIP', r'^MV2_USE_UD_HYBRID=.*' ],
    [ 'SKIP', r'^OMP_NUM_THREADS=.*' ],
    [ 'SKIP', r'^__.*'],
    [ 'SKIP', r'^LD_LIBRARY_PATH=.*'],
    [ 'SKIP', r'^I_MPI_INFO_NUMA_NODE_MAP=.*' ],
    [ 'SKIP', r'^I_MPI_INFO_NUMA_NODE_NUM=.*'],
    [ 'SKIP', r'^I_MPI_PIN_INFO=.*'],
    [ 'SKIP', r'^I_MPI_PIN_MAPPING=.*'],
    [ 'SKIP', r'^I_MPI_THREAD_LEVEL=.*'],
    [ 'SKIP', r'^I_MPI_TMI_PROVIDER=.*'],
    [ 'SKIP', r'^MV2_.*'],
    [ 'SKIP', r'^LAUNCHER_JID=.*'],
  ]

#------------------------------------------------------------
# Python pattern for python package tracking

# Note that sys, os, re, and subprocess can not be tracked due to the way that python tracking works.

python_pkg_patterns = [
  { 'k_s' : 'SKIP', 'kind' : 'path', 'patt' : r"^[^/]"               },  # SKIP all built-in packages
  { 'k_s' : 'SKIP', 'kind' : 'name', 'patt' : r"^_"                  },  # SKIP names that start with a underscore
  { 'k_s' : 'SKIP', 'kind' : 'name', 'patt' : r".*\."                },  # SKIP all names that are divided with periods: a.b.c
  { 'k_s' : 'KEEP', 'kind' : 'path', 'patt' : r".*/.local/"          },  # KEEP all packages installed by users
  { 'k_s' : 'KEEP', 'kind' : 'path', 'patt' : r".*/site-packages/"   },  # KEEP all site-packages
  { 'k_s' : 'SKIP', 'kind' : 'path', 'patt' : r"^/opt"               },  # SKIP all python packages in /opt except for ones in .*/site-packages/
  { 'k_s' : 'SKIP', 'kind' : 'path', 'patt' : r"^/home"              },  # SKIP all other packages in user locations
  { 'k_s' : 'SKIP', 'kind' : 'path', 'patt' : r"^/work"              },  # SKIP all other packages in user locations
  { 'k_s' : 'SKIP', 'kind' : 'path', 'patt' : r"^/scratch"           },  # SKIP all other packages in user locations
]
