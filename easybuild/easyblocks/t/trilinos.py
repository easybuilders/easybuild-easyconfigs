##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
EasyBuild support for Trilinos, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import re

from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_Trilinos(CMakeMake):
    """Support for building Trilinos."""
    # see http://trilinos.sandia.gov/Trilinos10CMakeQuickstart.txt

    @staticmethod
    def extra_options():
        """Add extra config options specific to Trilinos."""
        extra_vars = {
            'shared_libs': [False, "Build shared libs; if False, build static libs", CUSTOM],
            'openmp': [True, "Enable OpenMP support", CUSTOM],
            'all_exts': [True, "Enable all Trilinos packages", CUSTOM],
            'skip_exts': [[], "List of Trilinos packages to skip", CUSTOM],
            'verbose': [False, "Configure for verbose output", CUSTOM],
        }
        return CMakeMake.extra_options(extra_vars)

    def configure_step(self):
        """Set some extra environment variables before configuring."""

        # enable verbose output if desired
        if self.cfg['verbose']:
            for x in ["CONFIGURE", "MAKEFILE"]:
                self.cfg.update('configopts', "-DTrilinos_VERBOSE_%s:BOOL=ON" % x)

        # compiler flags
        cflags = [os.getenv('CFLAGS')]
        cxxflags = [os.getenv('CXXFLAGS')]
        fflags = [os.getenv('FFLAGS')]

        ignore_cxx_seek_mpis = [toolchain.INTELMPI, toolchain.MPICH, toolchain.MPICH2, toolchain.MVAPICH2]  #@UndefinedVariable
        ignore_cxx_seek_flag = "-DMPICH_IGNORE_CXX_SEEK"
        if self.toolchain.mpi_family() in ignore_cxx_seek_mpis:
            cflags.append(ignore_cxx_seek_flag)
            cxxflags.append(ignore_cxx_seek_flag)
            fflags.append(ignore_cxx_seek_flag)

        self.cfg.update('configopts', '-DCMAKE_C_FLAGS="%s"' % ' '.join(cflags))
        self.cfg.update('configopts', '-DCMAKE_CXX_FLAGS="%s"' % ' '.join(cxxflags))
        self.cfg.update('configopts', '-DCMAKE_Fortran_FLAGS="%s"' % ' '.join(fflags))

        # OpenMP
        if self.cfg['openmp']:
            self.cfg.update('configopts', "-DTrilinos_ENABLE_OpenMP:BOOL=ON")

        # MPI
        if self.toolchain.options.get('usempi', None):
            self.cfg.update('configopts', "-DTPL_ENABLE_MPI:BOOL=ON")

        # shared libraries
        if self.cfg['shared_libs']:
            self.cfg.update('configopts', "-DBUILD_SHARED_LIBS:BOOL=ON")
        else:
            self.cfg.update('configopts', "-DBUILD_SHARED_LIBS:BOOL=OFF")

        # release or debug get_version
        if self.toolchain.options['debug']:
            self.cfg.update('configopts', "-DCMAKE_BUILD_TYPE:STRING=DEBUG")
        else:
            self.cfg.update('configopts', "-DCMAKE_BUILD_TYPE:STRING=RELEASE")

        # enable full testing
        self.cfg.update('configopts', "-DTrilinos_ENABLE_TESTS:BOOL=ON")
        self.cfg.update('configopts', "-DTrilinos_ENABLE_ALL_FORWARD_DEP_PACKAGES:BOOL=ON")

        lib_re = re.compile("^lib(.*).a$")

        # BLAS, LAPACK
        for dep in ["BLAS", "LAPACK"]:
            self.cfg.update('configopts', '-DTPL_ENABLE_%s:BOOL=ON' % dep)
            libdirs = os.getenv('%s_LIB_DIR' % dep)
            if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
                libdirs += ";%s/lib64" % get_software_root('GCC')
            self.cfg.update('configopts', '-D%s_LIBRARY_DIRS="%s"' % (dep, libdirs))
            libs = os.getenv('%s_MT_STATIC_LIBS' % dep).split(',')
            lib_names = ';'.join([lib_re.search(l).group(1) for l in libs])
            if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
                # explicitely specify static lib!
                lib_names += ";libgfortran.a"
            self.cfg.update('configopts', '-D%s_LIBRARY_NAMES="%s"' % (dep, lib_names))

        # UMFPACK is part of SuiteSparse
        suitesparse = get_software_root('SuiteSparse')
        if suitesparse:
            self.cfg.update('configopts', "-DTPL_ENABLE_UMFPACK:BOOL=ON")
            incdirs, libdirs, libnames = [], [], []
            for lib in ["UMFPACK", "CHOLMOD", "COLAMD", "AMD"]:
                incdirs.append(os.path.join(suitesparse, lib, "Include"))
                libdirs.append(os.path.join(suitesparse, lib, "Lib"))
                libnames.append(lib.lower())
            # add SuiteSparse config lib, it is in recent versions of suitesparse
            libdirs.append(os.path.join(suitesparse, 'SuiteSparse_config'))
            libnames.append('suitesparseconfig')
            self.cfg.update('configopts', '-DUMFPACK_INCLUDE_DIRS:PATH="%s"' % ';'.join(incdirs))
            self.cfg.update('configopts', '-DUMFPACK_LIBRARY_DIRS:PATH="%s"' % ';'.join(libdirs))
            self.cfg.update('configopts', '-DUMFPACK_LIBRARY_NAMES:STRING="%s"' % ';'.join(libnames))

        # BLACS
        if get_software_root('BLACS'):
            self.cfg.update('configopts', "-DTPL_ENABLE_BLACS:BOOL=ON")
            self.cfg.update('configopts', '-DBLACS_INCLUDE_DIRS:PATH="%s"' % os.getenv('BLACS_INC_DIR'))
            self.cfg.update('configopts', '-DBLACS_LIBRARY_DIRS:PATH="%s"' % os.getenv('BLACS_LIB_DIR'))
            blacs_lib_names = os.getenv('BLACS_STATIC_LIBS').split(',')
            blacs_lib_names = [lib_re.search(x).group(1) for x in blacs_lib_names]
            self.cfg.update('configopts', '-DBLACS_LIBRARY_NAMES:STRING="%s"' % (';'.join(blacs_lib_names)))

        # ScaLAPACK
        if get_software_root('ScaLAPACK'):
            self.cfg.update('configopts', "-DTPL_ENABLE_SCALAPACK:BOOL=ON")
            self.cfg.update('configopts', '-DSCALAPACK_INCLUDE_DIRS:PATH="%s"' % os.getenv('SCALAPACK_INC_DIR'))
            self.cfg.update('configopts', '-DSCALAPACK_LIBRARY_DIRS:PATH="%s;%s"' % (os.getenv('SCALAPACK_LIB_DIR'),
                                                                                    os.getenv('BLACS_LIB_DIR')))
        # PETSc
        petsc = get_software_root('PETSc')
        if petsc:
            self.cfg.update('configopts', "-DTPL_ENABLE_PETSC:BOOL=ON")
            incdirs = [os.path.join(petsc, "include")]
            self.cfg.update('configopts', '-DPETSC_INCLUDE_DIRS:PATH="%s"' % ';'.join(incdirs))
            petsc_libdirs = [
                             os.path.join(petsc, "lib"),
                             os.path.join(suitesparse, "UMFPACK", "Lib"),
                             os.path.join(suitesparse, "CHOLMOD", "Lib"),
                             os.path.join(suitesparse, "COLAMD", "Lib"),
                             os.path.join(suitesparse, "AMD", "Lib"),
                             os.getenv('FFTW_LIB_DIR'),
                             os.path.join(get_software_root('ParMETIS'), "Lib")
                             ]
            self.cfg.update('configopts', '-DPETSC_LIBRARY_DIRS:PATH="%s"' % ';'.join(petsc_libdirs))
            petsc_libnames = ["petsc", "umfpack", "cholmod", "colamd", "amd", "parmetis", "metis"]
            petsc_libnames += [lib_re.search(x).group(1) for x in os.getenv('FFTW_STATIC_LIBS').split(',')]
            self.cfg.update('configopts', '-DPETSC_LIBRARY_NAMES:STRING="%s"' % ';'.join(petsc_libnames))

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
                self.cfg.update('configopts', "-DTPL_ENABLE_%s:BOOL=ON" % dep)
                incdir = os.path.join(deproot, "include")
                self.cfg.update('configopts', '-D%s_INCLUDE_DIRS:PATH="%s"' % (dep, incdir))
                libdir = os.path.join(deproot, "lib")
                self.cfg.update('configopts', '-D%s_LIBRARY_DIRS:PATH="%s"' % (dep, libdir))

        # extensions_step
        if self.cfg['all_exts']:
            self.cfg.update('configopts', "-DTrilinos_ENABLE_ALL_PACKAGES:BOOL=ON")

        else:
            for ext in self.cfg['exts_list']:
                self.cfg.update('configopts', "-DTrilinos_ENABLE_%s=ON" % ext)

        # packages to skip
        skip_exts = self.cfg['skip_exts']
        if skip_exts:
            for ext in skip_exts:
                self.cfg.update('configopts', "-DTrilinos_ENABLE_%s:BOOL=OFF" % ext)

        # building in source dir not supported
        try:
            build_dir = "BUILD"
            os.mkdir(build_dir)
            os.chdir(build_dir)
        except OSError, err:
            raise EasyBuildError("Failed to create and move into build directory: %s", err)

        # configure using cmake
        super(EB_Trilinos, self).configure_step(srcdir="..")

    def build_step(self):
        """Build with make (verbose logging enabled)."""
        super(EB_Trilinos, self).build_step(verbose=True)

    def sanity_check_step(self):
        """Custom sanity check for Trilinos."""

        # selection of libraries
        libs = ["Amesos", "Anasazi", "AztecOO", "Belos", "Epetra", "Galeri",
                "GlobiPack", "Ifpack", "Intrepid", "Isorropia", "Kokkos",
                "Komplex", "LOCA", "Mesquite", "ML", "Moertel", "MOOCHO", "NOX",
                "Pamgen", "RTOp", "Rythmos", "Sacado", "Shards", "Stratimikos",
                "Teuchos", "Tpetra", "Triutils", "Zoltan"]

        libs = [l for l in libs if not l in self.cfg['skip_exts']]

        # Teuchos was refactored in 11.2
        if LooseVersion(self.version) >= LooseVersion('11.2') and  'Teuchos' in libs:
            libs.remove('Teuchos')
            libs.extend(['teuchoscomm', 'teuchoscore', 'teuchosnumerics', 'teuchosparameterlist', 'teuchosremainder'])

        # Kokkos was refactored in 12.x, check for libkokkoscore.a rather than libkokkos.a
        if LooseVersion(self.version) >= LooseVersion('12') and 'Kokkos' in libs:
            libs.remove('Kokkos')
            libs.append('kokkoscore')

        custom_paths = {
            'files': [os.path.join('lib', 'lib%s.a' % x.lower()) for x in libs],
            'dirs': ['bin', 'include']
        }

        super(EB_Trilinos, self).sanity_check_step(custom_paths=custom_paths)
