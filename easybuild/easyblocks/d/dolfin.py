##
# Copyright 2012 Kenneth Hoste
# Copyright 2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
"""
import os
import re

import easybuild.tools.toolkit as toolkit
from easybuild.easyblocks.cmakepythonpackage import EB_CMakePythonPackage
from easybuild.tools.modules import get_software_root, get_software_version


class EB_DOLFIN(EB_CMakePythonPackage):
    """Support for building and installing DOLFIN."""

    def configure(self):
        """Set DOLFIN-specific configure options and configure with CMake."""

        # compilers
        self.updatecfg('configopts', "-DCMAKE_C_COMPILER='%s' " % os.getenv('CC'))
        self.updatecfg('configopts', "-DCMAKE_CXX_COMPILER='%s' " % os.getenv('CXX'))
        self.updatecfg('configopts', "-DCMAKE_Fortran_COMPILER='%s' " % os.getenv('F90'))

        # compiler flags
        cflags = os.getenv('CFLAGS')
        cxxflags = os.getenv('CXXFLAGS')
        fflags = os.getenv('FFLAGS')

        # fix for "SEEK_SET is #defined but must not be for the C++ binding of MPI. Include mpi.h before stdio.h"
        if self.toolkit().mpi_type() in [toolkit.INTEL, toolkit.MPICH2]:
            cflags += " -DMPICH_IGNORE_CXX_SEEK"
            cxxflags += " -DMPICH_IGNORE_CXX_SEEK"
            fflags += " -DMPICH_IGNORE_CXX_SEEK"

        self.updatecfg('configopts', '-DCMAKE_C_FLAGS="%s"' % cflags)
        self.updatecfg('configopts', '-DCMAKE_CXX_FLAGS="%s"' % cxxflags)
        self.updatecfg('configopts', '-DCMAKE_Fortran_FLAGS="%s"' % fflags)

        # run cmake in debug mode
        self.updatecfg('configopts', ' -DCMAKE_BUILD_TYPE=Debug')

        # set correct compilers to be used at runtime
        self.updatecfg('configopts', ' -DMPI_C_COMPILER="$MPICC"')
        self.updatecfg('configopts', ' -DMPI_CXX_COMPILER="$MPICXX"')

        # specify MPI library
        self.updatecfg('configopts', ' -DMPI_COMPILER="%s"' % os.getenv('MPICC'))

        if  os.getenv('MPI_LIB_SHARED') and os.getenv('MPI_INC_DIR'):
            self.updatecfg('configopts', ' -DMPI_LIBRARY="%s"' % os.getenv('MPI_LIB_SHARED'))
            self.updatecfg('configopts', ' -DMPI_INCLUDE_PATH="%s"' % os.getenv('MPI_INC_DIR'))
        else:
            self.log.error('MPI_LIB_SHARED or MPI_INC_DIR not set, could not determine MPI-related paths.')

        # save config options to reuse them later (e.g. for sanity check commands)
        self.saved_configopts = self.getcfg('configopts')

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
        self.updatecfg('configopts', '-DZLIB_INCLUDE_DIR=%s' % os.path.join(depsdict['zlib'], "include"))
        self.updatecfg('configopts', '-DZLIB_LIBRARY=%s' % os.path.join(depsdict['zlib'], "lib", "libz.a"))

        # set correct openmp options
        openmp = self.toolkit().get_openmp_flag()
        self.updatecfg('configopts', ' -DOpenMP_CXX_FLAGS="%s"' % openmp)
        self.updatecfg('configopts', ' -DOpenMP_C_FLAGS="%s"' % openmp)

        # Boost config parameters
        self.updatecfg('configopts', " -DBOOST_INCLUDEDIR=%s/include" % depsdict['Boost'])
        self.updatecfg('configopts', " -DBoost_DEBUG=ON -DBOOST_ROOT=%s" % depsdict['Boost'])

        # UFC and Armadillo config params
        self.updatecfg('configopts', " -DUFC_DIR=%s" % depsdict['UFC'])
        self.updatecfg('configopts', "-DARMADILLO_DIR:PATH=%s " % depsdict['Armadillo'])

        # specify Python paths
        python_short_ver = ".".join(get_software_version('Python').split(".")[0:2])
        self.updatecfg('configopts', " -DPYTHON_INCLUDE_PATH=%s/include/python%s" % (depsdict['Python'],
                                                                                     python_short_ver))
        self.updatecfg('configopts', " -DPYTHON_LIBRARY=%s/lib/libpython%s.so" % (depsdict['Python'],
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

        self.updatecfg('configopts', ' '.join(umfpack_params) % {'sp':suitesparse})

        # ParMETIS and SCOTCH
        self.updatecfg('configopts', '-DPARMETIS_DIR="%s"' % depsdict['ParMETIS'])
        self.updatecfg('configopts', '-DSCOTCH_DIR="%s" -DSCOTCH_DEBUG:BOOL=ON' % depsdict['SCOTCH'])

        # BLACS and LAPACK 
        self.updatecfg('configopts', '-DBLAS_LIBRARIES:PATH="%s"' % os.getenv('LIBBLAS'))
        self.updatecfg('configopts', '-DLAPACK_LIBRARIES:PATH="%s"' % os.getenv('LIBLAPACK'))

        # CGAL
        self.updatecfg('configopts', '-DCGAL_DIR:PATH="%s"' % depsdict['CGAL'])

        # PETSc
        # need to specify PETSC_ARCH explicitely (env var alone is not sufficient)
        for env_var in ["PETSC_DIR", "PETSC_ARCH"]:
            val = os.getenv(env_var)
            if val:
                self.updatecfg('configopts', '-D%s=%s' % (env_var, val))

        # MTL4
        self.updatecfg('configopts', '-DMTL4_DIR:PATH="%s"' % depsdict['MTL4'])

        # configure
        out = EB_CMakePythonPackage.configure(self)

        # make sure that all optional packages are found
        not_found_re = re.compile("The following optional packages could not be found")
        if not_found_re.search(out):
            self.log.error("Optional packages could not be found, this should not happen...")

    def make_module_extra(self):
        """Set extra environment variables for DOLFIN."""

        txt = EB_CMakePythonPackage.make_module_extra(self)

        # Dolfin needs to find Boost and the UFC pkgconfig file
        txt += self.moduleGenerator.setEnvironment('BOOST_DIR', get_software_root('Boost'))
        pkg_config_paths = [os.path.join(get_software_root('UFC'), "lib", "pkgconfig"),
                            os.path.join(self.installdir, "lib", "pkgconfig")]
        txt += self.moduleGenerator.prependPaths("PKG_CONFIG_PATH", pkg_config_paths)

        envvars = ['I_MPI_CXX', 'I_MPI_CC']
        for envvar in envvars:
            envar_val = os.getenv(envvar)
            # if environment variable is set, also set it in module
            if envar_val:
                txt += self.moduleGenerator.setEnvironment(envvar, envar_val)

        return txt

    def sanitycheck(self):
        """Custom sanity check for DOLFIN."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {
                                             'files': ['bin/dolfin-%s' % x for x in ['version', 'convert',
                                                                                     'order', 'plot']]
                                                    + ['include/dolfin.h'],
                                             'dirs':['%s/dolfin' % self.pylibdir]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        if not self.getcfg('sanityCheckCommands'):

            pref = os.path.join('share', 'dolfin', 'demo')

            # test command templates
            cmd_template_python = " && ".join(["cd %(dir)s", "python demo_%(name)s.py", "cd -"])

            cmd_template_cpp = " && ".join(["cd %(dir)s", "cmake . %s" % self.saved_configopts,
                                            "make", "./demo_%(name)s", "cd -"])

            # list based on demos available for DOLFIN v1.0.0
            pde_demos = ['biharmonic', 'cahn-hilliard', 'hyperelasticity', 'mixed-poisson',
                         'navier-stokes', 'poisson', 'stokes-iterative']

            demos = [os.path.join('la', 'eigenvalue')] + [os.path.join('pde', x) for x in pde_demos]

            # construct commands
            cmds = [tmpl % {
                            'dir': os.path.join(pref, d, subdir),
                            'name': os.path.basename(d),
                           }
                    for d in demos
                    for (tmpl, subdir) in [(cmd_template_python, 'python'), (cmd_template_cpp, 'cpp')]]

            # subdomains-poisson has no C++ version, only Python
            name = 'subdomains-poisson'
            path = os.path.join(pref, 'pde', name, 'python')
            cmds += [cmd_template_python % {'dir': path, 'name': name}]

            # supply empty argument to each command
            cmds = [(cmd, "") for cmd in cmds]

            # join all commands into one large single sanity check command
            self.setcfg('sanityCheckCommands', cmds)

        EB_CMakePythonPackage.sanitycheck(self)
