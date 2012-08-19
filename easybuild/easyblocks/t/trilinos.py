# Copyright 2012 Kenneth Hoste
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
EasyBuild support for Trilinos, implemented as an easyblock
"""
import os
import re

import easybuild.tools.toolkit as toolkit
from easybuild.easyblocks.c.cmake import EB_CMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.modules import get_software_root


class EB_Trilinos(EB_CMake):
    """Support for building Trilinos."""
    # see http://trilinos.sandia.gov/Trilinos10CMakeQuickstart.txt

    @staticmethod
    def extra_options():
        """Add extra config options specific to Trilinos."""
        extra_vars = [
                      ('shared_libs', [False, "BUild shared libs; if False, build static libs. (default: False).", CUSTOM]),
                      ('openmp', [True, "Enable OpenMP support (default: True)", CUSTOM]),
                      ('all_pkgs', [True, "Enable all packages (default: True)", CUSTOM]),
                      ('skip_pkgs', [[], "List of packages to skip (default: [])", CUSTOM]),
                      ('verbose', [False, 'Configure for verbose output (default: False)', CUSTOM])
                     ]
        return EB_CMake.extra_options(extra_vars)

    def configure(self):
        """Set some extra environment variables before configuring."""

        # enable verbose output if desired
        if self.getcfg('verbose'):
            for x in ["CONFIGURE", "MAKEFILE"]:
                self.updatecfg('configopts', "-DTrilinos_VERBOSE_%s:BOOL=ON" % x)

        # compiler flags
        cflags = os.getenv('CFLAGS')
        cxxflags = os.getenv('CXXFLAGS')
        fflags = os.getenv('FFLAGS')

        if self.toolkit().mpi_type() in [toolkit.INTEL, toolkit.MPICH2]:
            cflags += " -DMPICH_IGNORE_CXX_SEEK"
            cxxflags += " -DMPICH_IGNORE_CXX_SEEK"
            fflags += " -DMPICH_IGNORE_CXX_SEEK"

        self.updatecfg('configopts', '-DCMAKE_C_FLAGS="%s"' % cflags)
        self.updatecfg('configopts', '-DCMAKE_CXX_FLAGS="%s"' % cxxflags)
        self.updatecfg('configopts', '-DCMAKE_Fortran_FLAGS="%s"' % fflags)

        # OpenMP
        if self.getcfg('openmp'):
            self.updatecfg('configopts', "-DTrilinos_ENABLE_OpenMP:BOOL=ON")

        # MPI
        if self.toolkit().opts['usempi']:
            self.updatecfg('configopts', "-DTPL_ENABLE_MPI:BOOL=ON")

        # shared libraries
        if self.getcfg('shared_libs'):
            self.updatecfg('configopts', "-DBUILD_SHARED_LIBS:BOOL=ON")
        else:
            self.updatecfg('configopts', "-DBUILD_SHARED_LIBS:BOOL=OFF")

        # release or debug version
        if self.toolkit().opts['debug']:
            self.updatecfg('configopts', "-DCMAKE_BUILD_TYPE:STRING=DEBUG")
        else:
            self.updatecfg('configopts', "-DCMAKE_BUILD_TYPE:STRING=RELEASE")

        # enable full testing
        self.updatecfg('configopts', "-DTrilinos_ENABLE_TESTS:BOOL=ON")
        self.updatecfg('configopts', "-DTrilinos_ENABLE_ALL_FORWARD_DEP_PACKAGES:BOOL=ON")

        lib_re = re.compile("^lib(.*).a$")

        # BLAS, LAPACK
        for dep in ["BLAS", "LAPACK"]:
            self.updatecfg('configopts', '-DTPL_ENABLE_%s:BOOL=ON' % dep)
            libdirs = os.getenv('%s_LIB_DIR' % dep)
            if self.toolkit().comp_family() == toolkit.GCC:
                libdirs += ";%s/lib64" % get_software_root('GCC')
            self.updatecfg('configopts', '-D%s_LIBRARY_DIRS="%s"' % (dep, libdirs))
            libs = os.getenv('%s_MT_STATIC_LIBS' % dep).split(',')
            lib_names = ';'.join([lib_re.search(l).group(1) for l in libs])
            if self.toolkit().comp_family() == toolkit.GCC:
                # explicitely specify static lib!
                lib_names += ";libgfortran.a"
            self.updatecfg('configopts', '-D%s_LIBRARY_NAMES="%s"' % (dep, lib_names))

        # UMFPACK is part of SuiteSparse
        suitesparse = get_software_root('SuiteSparse')
        if suitesparse:
            self.updatecfg('configopts', "-DTPL_ENABLE_UMFPACK:BOOL=ON")
            incdirs, libdirs, libnames = [], [], []
            for lib in ["UMFPACK", "CHOLMOD", "COLAMD", "AMD"]:
                incdirs.append(os.path.join(suitesparse, lib, "Include"))
                libdirs.append(os.path.join(suitesparse, lib, "Lib"))
                libnames.append(lib.lower())
            self.updatecfg('configopts', '-DUMFPACK_INCLUDE_DIRS:PATH="%s"' % ';'.join(incdirs))
            self.updatecfg('configopts', '-DUMFPACK_LIBRARY_DIRS:PATH="%s"' % ';'.join(libdirs))
            self.updatecfg('configopts', '-DUMFPACK_LIBRARY_NAMES:STRING="%s"' % ';'.join(libnames))

        # BLACS
        if get_software_root('BLACS'):
            self.updatecfg('configopts', "-DTPL_ENABLE_BLACS:BOOL=ON")
            self.updatecfg('configopts', '-DBLACS_INCLUDE_DIRS:PATH="%s"' % os.getenv('BLACS_INC_DIR'))
            self.updatecfg('configopts', '-DBLACS_LIBRARY_DIRS:PATH="%s"' % os.getenv('BLACS_LIB_DIR'))
            blacs_lib_names = os.getenv('BLACS_STATIC_LIBS').split(',')
            blacs_lib_names = [lib_re.search(x).group(1) for x in blacs_lib_names]
            self.updatecfg('configopts', '-DBLACS_LIBRARY_NAMES:STRING="%s"' % (';'.join(blacs_lib_names)))

        # ScaLAPACK
        if get_software_root('ScaLAPACK'):
            self.updatecfg('configopts', "-DTPL_ENABLE_SCALAPACK:BOOL=ON")
            self.updatecfg('configopts', '-DSCALAPACK_INCLUDE_DIRS:PATH="%s"' % os.getenv('SCALAPACK_INC_DIR'))
            self.updatecfg('configopts', '-DSCALAPACK_LIBRARY_DIRS:PATH="%s;%s"' % (os.getenv('SCALAPACK_LIB_DIR'),
                                                                                    os.getenv('BLACS_LIB_DIR')))

        # PETSc
        petsc = get_software_root('PETSc')
        if petsc:
            self.updatecfg('configopts', "-DTPL_ENABLE_PETSC:BOOL=ON")
            incdirs = [os.path.join(petsc, "include")]
            self.updatecfg('configopts', '-DPETSC_INCLUDE_DIRS:PATH="%s"' % ';'.join(incdirs))
            petsc_libdirs = [
                             os.path.join(petsc, "lib"),
                             os.path.join(suitesparse, "UMFPACK", "Lib"),
                             os.path.join(suitesparse, "CHOLMOD", "Lib"),
                             os.path.join(suitesparse, "COLAMD", "Lib"),
                             os.path.join(suitesparse, "AMD", "Lib"),
                             os.getenv('FFTW_LIB_DIR'),
                             os.path.join(get_software_root('ParMETIS'), "Lib")
                             ]
            self.updatecfg('configopts', '-DPETSC_LIBRARY_DIRS:PATH="%s"' % ';'.join(petsc_libdirs))
            petsc_libnames = ["petsc", "umfpack", "cholmod", "colamd", "amd", "parmetis", "metis"]
            petsc_libnames += [lib_re.search(x).group(1) for x in os.getenv('FFTW_STATIC_LIBS').split(',')]
            self.updatecfg('configopts', '-DPETSC_LIBRARY_NAMES:STRING="%s"' % ';'.join(petsc_libnames))

        # other Third-Party Libraries (TPLs)
        deps = self.cfg.dependencies()
        builddeps = self.cfg.builddependencies() + ["SuiteSparse"]
        deps = [dep['name'] for dep in deps if not dep['name'] in builddeps]
        for dep in deps:
            deproot = get_software_root(dep)
            if deproot:
                depmap = {
                          'SCOTCH': 'Scotch',
                          }
                dep = depmap.get(dep, dep)
                self.updatecfg('configopts', "-DTPL_ENABLE_%s:BOOL=ON" % dep)
                incdir = os.path.join(deproot, "include")
                self.updatecfg('configopts', '-D%s_INCLUDE_DIRS:PATH="%s"' % (dep, incdir))
                libdir = os.path.join(deproot, "lib")
                self.updatecfg('configopts', '-D%s_LIBRARY_DIRS:PATH="%s"' % (dep, libdir))

        # packages
        if self.getcfg('all_pkgs'):
            self.updatecfg('configopts', "-DTrilinos_ENABLE_ALL_PACKAGES:BOOL=ON")

        else:
            for pkg in self.getcfg('pkglist'):
                self.updatecfg('configopts', "-DTrilinos_ENABLE_%s=ON" % pkg)

        # packages to skip
        skip_pkgs = self.getcfg('skip_pkgs')
        if skip_pkgs:
            for pkg in skip_pkgs:
                self.updatecfg('configopts', "-DTrilinos_ENABLE_%s:BOOL=OFF" % pkg)

        # building in source dir not supported
        try:
            build_dir = "BUILD"
            os.mkdir(build_dir)
            os.chdir(build_dir)
        except OSError, err:
            self.log.error("Failed to create and move into build directory: %s" % err)

        # configure using cmake
        EB_CMake.configure(self, "..")

    def make(self):
        """Build with make (verbose logging enabled)."""
        EB_CMake.make(self, verbose=True)

    def sanitycheck(self):
        """Custom sanity check for Trilinos."""

        if not self.getcfg('sanityCheckPaths'):

            # selection of libraries
            libs = ["Amesos", "Anasazi", "AztecOO", "Belos", "Epetra", "Galeri",
                    "GlobiPack", "Ifpack", "Intrepid", "Isorropia", "Kokkos",
                    "Komplex", "LOCA", "Mesquite", "ML", "Moertel", "MOOCHO", "NOX",
                    "Pamgen", "RTOp", "Rythmos", "Sacado", "Shards", "Stratimikos",
                    "Teuchos", "Tpetra", "Triutils", "Zoltan"]

            libs = [l for l in libs if not l in self.getcfg('skip_pkgs')]

            self.setcfg('sanityCheckPaths', {
                                             'files':[os.path.join("lib", "lib%s.a" % x.lower()) for x in libs],
                                             'dirs':['bin', 'include']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        EB_CMake.sanitycheck(self)
