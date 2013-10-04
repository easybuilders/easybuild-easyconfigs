##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for DOLFIN, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import re
import tempfile

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.cmakepythonpackage import CMakePythonPackage
from easybuild.tools.filetools import rmtree2
from easybuild.tools.modules import get_software_root, get_software_version


class EB_DOLFIN(CMakePythonPackage):
    """Support for building and installing DOLFIN."""

    def __init__(self, *args, **kwargs):
        """Initialize class variables."""
        super(EB_DOLFIN, self).__init__(*args, **kwargs)

        self.boost_dir = None
        self.saved_configopts = None

    def configure_step(self):
        """Set DOLFIN-specific configure options and configure with CMake."""

        # compilers
        self.cfg.update('configopts', "-DCMAKE_C_COMPILER='%s' " % os.getenv('CC'))
        self.cfg.update('configopts', "-DCMAKE_CXX_COMPILER='%s' " % os.getenv('CXX'))
        self.cfg.update('configopts', "-DCMAKE_Fortran_COMPILER='%s' " % os.getenv('F90'))

        # compiler flags
        cflags = os.getenv('CFLAGS')
        cxxflags = os.getenv('CXXFLAGS')
        fflags = os.getenv('FFLAGS')

        # fix for "SEEK_SET is #defined but must not be for the C++ binding of MPI. Include mpi.h before stdio.h"
        if self.toolchain.mpi_family() in [toolchain.INTELMPI, toolchain.MPICH2, toolchain.MVAPICH2]:
            cflags += " -DMPICH_IGNORE_CXX_SEEK"
            cxxflags += " -DMPICH_IGNORE_CXX_SEEK"
            fflags += " -DMPICH_IGNORE_CXX_SEEK"

        self.cfg.update('configopts', '-DCMAKE_C_FLAGS="%s"' % cflags)
        self.cfg.update('configopts', '-DCMAKE_CXX_FLAGS="%s"' % cxxflags)
        self.cfg.update('configopts', '-DCMAKE_Fortran_FLAGS="%s"' % fflags)

        # run cmake in debug mode
        self.cfg.update('configopts', ' -DCMAKE_BUILD_TYPE=Debug')

        # set correct compilers to be used at runtime
        self.cfg.update('configopts', ' -DMPI_C_COMPILER="$MPICC"')
        self.cfg.update('configopts', ' -DMPI_CXX_COMPILER="$MPICXX"')

        # specify MPI library
        self.cfg.update('configopts', ' -DMPI_COMPILER="%s"' % os.getenv('MPICC'))

        if  os.getenv('MPI_LIB_SHARED') and os.getenv('MPI_INC_DIR'):
            self.cfg.update('configopts', ' -DMPI_LIBRARY="%s"' % os.getenv('MPI_LIB_SHARED'))
            self.cfg.update('configopts', ' -DMPI_INCLUDE_PATH="%s"' % os.getenv('MPI_INC_DIR'))
        else:
            self.log.error('MPI_LIB_SHARED or MPI_INC_DIR not set, could not determine MPI-related paths.')

        # save config options to reuse them later (e.g. for sanity check commands)
        self.saved_configopts = self.cfg['configopts']

        # make sure that required dependencies are loaded
        deps = ['Armadillo', 'Boost', 'CGAL', 'MTL4', 'ParMETIS', 'PETSc', 'Python',
                'SCOTCH', 'Sphinx', 'SLEPc', 'SuiteSparse', 'Trilinos', 'UFC', 'zlib']
        depsdict = {}
        for dep in deps:
            deproot = get_software_root(dep)
            if not deproot:
                self.log.error("Dependency %s not available." % dep)
            else:
                depsdict.update({dep:deproot})

        # zlib
        self.cfg.update('configopts', '-DZLIB_INCLUDE_DIR=%s' % os.path.join(depsdict['zlib'], "include"))
        self.cfg.update('configopts', '-DZLIB_LIBRARY=%s' % os.path.join(depsdict['zlib'], "lib", "libz.a"))

        # set correct openmp options
        openmp = self.toolchain.get_flag('openmp')
        self.cfg.update('configopts', ' -DOpenMP_CXX_FLAGS="%s"' % openmp)
        self.cfg.update('configopts', ' -DOpenMP_C_FLAGS="%s"' % openmp)

        # Boost config parameters
        self.cfg.update('configopts', " -DBOOST_INCLUDEDIR=%s/include" % depsdict['Boost'])
        self.cfg.update('configopts', " -DBoost_DEBUG=ON -DBOOST_ROOT=%s" % depsdict['Boost'])
        self.boost_dir = depsdict['Boost']

        # UFC and Armadillo config params
        self.cfg.update('configopts', " -DUFC_DIR=%s" % depsdict['UFC'])
        self.cfg.update('configopts', "-DARMADILLO_DIR:PATH=%s " % depsdict['Armadillo'])

        # specify Python paths
        python_short_ver = ".".join(get_software_version('Python').split(".")[0:2])
        self.cfg.update('configopts', " -DPYTHON_INCLUDE_PATH=%s/include/python%s" % (depsdict['Python'],
                                                                                     python_short_ver))
        self.cfg.update('configopts', " -DPYTHON_LIBRARY=%s/lib/libpython%s.so" % (depsdict['Python'],
                                                                                  python_short_ver))

        # SuiteSparse config params
        suitesparse = depsdict['SuiteSparse']
        umfpack_params = [
                          ' -DUMFPACK_DIR="%(sp)s/UMFPACK"',
                          '-DUMFPACK_INCLUDE_DIRS="%(sp)s/UMFPACK/include;%(sp)s/UFconfig"',
                          '-DAMD_DIR="%(sp)s/UMFPACK"',
                          '-DCHOLMOD_DIR="%(sp)s/CHOLMOD"',
                          '-DCHOLMOD_INCLUDE_DIRS="%(sp)s/CHOLMOD/include;%(sp)s/UFconfig"',
                          '-DUFCONFIG_DIR="%(sp)s/UFconfig"',
                          '-DCAMD_LIBRARY:PATH="%(sp)s/CAMD/lib/libcamd.a"',
                          '-DCCOLAMD_LIBRARY:PATH="%(sp)s/CCOLAMD/lib/libccolamd.a"',
                          '-DCOLAMD_LIBRARY:PATH="%(sp)s/COLAMD/lib/libcolamd.a"'
                          ]

        self.cfg.update('configopts', ' '.join(umfpack_params) % {'sp':suitesparse})

        # ParMETIS and SCOTCH
        self.cfg.update('configopts', '-DPARMETIS_DIR="%s"' % depsdict['ParMETIS'])
        self.cfg.update('configopts', '-DSCOTCH_DIR="%s" -DSCOTCH_DEBUG:BOOL=ON' % depsdict['SCOTCH'])

        # BLACS and LAPACK 
        self.cfg.update('configopts', '-DBLAS_LIBRARIES:PATH="%s"' % os.getenv('LIBBLAS'))
        self.cfg.update('configopts', '-DLAPACK_LIBRARIES:PATH="%s"' % os.getenv('LIBLAPACK'))

        # CGAL
        self.cfg.update('configopts', '-DCGAL_DIR:PATH="%s"' % depsdict['CGAL'])

        # PETSc
        # need to specify PETSC_ARCH explicitely (env var alone is not sufficient)
        for env_var in ["PETSC_DIR", "PETSC_ARCH"]:
            val = os.getenv(env_var)
            if val:
                self.cfg.update('configopts', '-D%s=%s' % (env_var, val))

        # MTL4
        self.cfg.update('configopts', '-DMTL4_DIR:PATH="%s"' % depsdict['MTL4'])

        # configure
        out = super(EB_DOLFIN, self).configure_step()

        # make sure that all optional packages are found
        not_found_re = re.compile("The following optional packages could not be found")
        if not_found_re.search(out):
            self.log.error("Optional packages could not be found, this should not happen...")

        # enable verbose build, so we have enough information if something goes wrong
        self.cfg.update('makeopts', "VERBOSE=1")

    def make_module_extra(self):
        """Set extra environment variables for DOLFIN."""

        txt = super(EB_DOLFIN, self).make_module_extra()

        # Dolfin needs to find Boost
        txt += self.moduleGenerator.set_environment('BOOST_DIR', self.boost_dir)

        envvars = ['I_MPI_CXX', 'I_MPI_CC']
        for envvar in envvars:
            envar_val = os.getenv(envvar)
            # if environment variable is set, also set it in module
            if envar_val:
                txt += self.moduleGenerator.set_environment(envvar, envar_val)

        return txt

    def sanity_check_step(self):
        """Custom sanity check for DOLFIN."""

        # custom sanity check paths
        custom_paths = {
                         'files': ['bin/dolfin-%s' % x for x in ['version', 'convert', 'order', 'plot']] +
                                  ['include/dolfin.h'],
                         'dirs':['%s/dolfin' % self.pylibdir]
                        }

        # custom sanity check commands

        # set cache/error dirs for Instant
        tmpdir = tempfile.mkdtemp()
        instant_cache_dir = os.path.join(tmpdir, '.instant', 'cache')
        instant_error_dir = os.path.join(tmpdir, '.instant', 'error')
        try:
            os.makedirs(instant_cache_dir)
            os.makedirs(instant_error_dir)
        except OSError, err:
            self.log.error("Failed to create Instant cache/error dirs: %s" % err)

        # keep track of $LDFLAGS, so we can restore them for the sanity check commands
        # this is required to make sure that linking of libraries (OpenBLAS, etc.) works as expected
        ldflags = os.getenv('LDFLAGS')

        # we need to explicitely set the following environment variables as a part of the sanity check command,
        # because the environment is reset and only the environment variables set by the DOLFIN module are there
        env_vars = [
            ('LDFLAGS', ldflags),
            ('INSTANT_CACHE_DIR', instant_cache_dir),
            ('INSTANT_ERROR_DIR', instant_error_dir),
        ]
        env_var_cmds = ' && '.join(['export %s="%s"' % (var, val) for (var, val) in env_vars])

        pref = os.path.join('share', 'dolfin', 'demo')

        # test command templates
        cmd_template_python = " && ".join([
            env_var_cmds,
            "cd %(dir)s",
            "python demo_%(name)s.py",
            "cd -",
        ])

        cmd_template_cpp = " && ".join([
            env_var_cmds,
            "cd %(dir)s",
            "cmake . %s" % self.saved_configopts,
            "make VERBOSE=1",
            "./demo_%(name)s",
            "cd -",
        ])

        # list based on demos available for DOLFIN v1.0.0
        pde_demos = ['biharmonic', 'cahn-hilliard', 'hyperelasticity', 'mixed-poisson',
                     'navier-stokes', 'poisson', 'stokes-iterative']

        demos = [os.path.join('la', 'eigenvalue')] + [os.path.join('pde', x) for x in pde_demos]

        # construct commands
        cmds = [
                tmpl % {
                        'dir': os.path.join(pref, d, subdir),
                        'name': os.path.basename(d),
                       }
                for d in demos
                for (tmpl, subdir) in [(cmd_template_cpp, 'cpp')]
               ]
                # exclude Python tests for now, because they 'hang' sometimes (unclear why)
                # they can be reinstated once run_cmd (or its equivalent) has support for timeouts
                # see https://github.com/hpcugent/easybuild-framework/issues/581
                #for (tmpl, subdir) in [(cmd_template_python, 'python'), (cmd_template_cpp, 'cpp')]]

        # subdomains-poisson has no C++ get_version, only Python
        # Python tests excluded, see above
        #name = 'subdomains-poisson'
        #path = os.path.join(pref, 'pde', name, 'python')
        #cmds += [cmd_template_python % {'dir': path, 'name': name}]

        # supply empty argument to each command
        custom_commands = [(cmd, "") for cmd in cmds]

        super(EB_DOLFIN, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

        # clean up temporary dir
        try:
            rmtree2(tmpdir)
        except OSError, err:
            self.log.error("Failed to remove Instant cache/error dirs: %s" % err)
