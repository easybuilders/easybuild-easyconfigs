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
EasyBuild support for PETSc, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import re
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import BUILD, CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_PETSc(ConfigureMake):
    """Support for building and installing PETSc"""

    def __init__(self, *args, **kwargs):
        """Initialize PETSc specific variables."""
        super(EB_PETSc, self).__init__(*args, **kwargs)

        self.petsc_arch = ""
        self.petsc_subdir = ""

    @staticmethod
    def extra_options():
        """Add extra config options specific to PETSc."""
        extra_vars = {
            'sourceinstall': [False, "Indicates whether a source installation should be performed", CUSTOM],
            'shared_libs': [False, "Build shared libraries", CUSTOM],
            'with_papi': [False, "Enable PAPI support", CUSTOM],
            'papi_inc': ['/usr/include', "Path for PAPI include files", CUSTOM],
            'papi_lib': ['/usr/lib64/libpapi.so', "Path for PAPI library", CUSTOM],
            'runtest': ['test', "Make target to test build", BUILD],
        }
        return ConfigureMake.extra_options(extra_vars)

    def make_builddir(self):
        """Decide whether or not to build in install dir before creating build dir."""

        if self.cfg['sourceinstall']:
            self.build_in_installdir = True

        super(EB_PETSc, self).make_builddir()

    def configure_step(self):
        """
        Configure PETSc by setting configure options and running configure script.

        Configure procedure is much more concise for older versions (< v3).
        """
        if LooseVersion(self.version) >= LooseVersion("3"):

            # compilers
            self.cfg.update('configopts', '--with-cc="%s"' % os.getenv('CC'))
            self.cfg.update('configopts', '--with-cxx="%s" --with-c++-support' % os.getenv('CXX'))
            self.cfg.update('configopts', '--with-fc="%s"' % os.getenv('F90'))

            # compiler flags
            if LooseVersion(self.version) >= LooseVersion("3.5"):
                self.cfg.update('configopts', '--CFLAGS="%s"' % os.getenv('CFLAGS'))
                self.cfg.update('configopts', '--CXXFLAGS="%s"' % os.getenv('CXXFLAGS'))
                self.cfg.update('configopts', '--FFLAGS="%s"' % os.getenv('F90FLAGS'))
            else:
                self.cfg.update('configopts', '--with-cflags="%s"' % os.getenv('CFLAGS'))
                self.cfg.update('configopts', '--with-cxxflags="%s"' % os.getenv('CXXFLAGS'))
                self.cfg.update('configopts', '--with-fcflags="%s"' % os.getenv('F90FLAGS'))

            if not self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
                self.cfg.update('configopts', '--with-gnu-compilers=0')

            # MPI
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', '--with-mpi=1')

            # build options
            self.cfg.update('configopts', '--with-build-step-np=%s' % self.cfg['parallel'])
            self.cfg.update('configopts', '--with-shared-libraries=%d' % self.cfg['shared_libs'])
            self.cfg.update('configopts', '--with-debugging=%d' % self.toolchain.options['debug'])
            self.cfg.update('configopts', '--with-pic=%d' % self.toolchain.options['pic'])
            self.cfg.update('configopts', '--with-x=0 --with-windows-graphics=0')

            # PAPI support
            if self.cfg['with_papi']:
                papi_inc = self.cfg['papi_inc']
                papi_inc_file = os.path.join(papi_inc, "papi.h")
                papi_lib = self.cfg['papi_lib']
                if os.path.isfile(papi_inc_file) and os.path.isfile(papi_lib):
                    self.cfg.update('configopts', '--with-papi=1')
                    self.cfg.update('configopts', '--with-papi-include=%s' % papi_inc)
                    self.cfg.update('configopts', '--with-papi-lib=%s' % papi_lib)
                else:
                    raise EasyBuildError("PAPI header (%s) and/or lib (%s) not found, can not enable PAPI support?",
                                         papi_inc_file, papi_lib)

            # Python extensions_step
            if get_software_root('Python'):
                self.cfg.update('configopts', '--with-numpy=1')
                if self.cfg['shared_libs']:
                    self.cfg.update('configopts', '--with-mpi4py=1')

            # FFTW, ScaLAPACK (and BLACS for older PETSc versions)
            deps = ["FFTW", "ScaLAPACK"]
            if LooseVersion(self.version) < LooseVersion("3.5"):
                deps.append("BLACS")
            for dep in deps:
                inc = os.getenv('%s_INC_DIR' % dep.upper())
                libdir = os.getenv('%s_LIB_DIR' % dep.upper())
                libs = os.getenv('%s_STATIC_LIBS' % dep.upper())
                if inc and libdir and libs:
                    with_arg = "--with-%s" % dep.lower()
                    self.cfg.update('configopts', '%s=1' % with_arg)
                    self.cfg.update('configopts', '%s-include=%s' % (with_arg, inc))
                    self.cfg.update('configopts', '%s-lib=[%s/%s]' % (with_arg, libdir, libs))
                else:
                    self.log.info("Missing inc/lib info, so not enabling %s support." % dep)

            # BLAS, LAPACK libraries
            bl_libdir = os.getenv('BLAS_LAPACK_LIB_DIR')
            bl_libs = os.getenv('BLAS_LAPACK_STATIC_LIBS')
            if bl_libdir and bl_libs:
                self.cfg.update('configopts', '--with-blas-lapack-lib=[%s/%s]' % (bl_libdir, bl_libs))
            else:
                raise EasyBuildError("One or more environment variables for BLAS/LAPACK not defined?")

            # additional dependencies
            # filter out deps handled seperately
            depfilter = self.cfg.builddependencies() + ["BLACS", "BLAS", "CMake", "FFTW", "LAPACK", "numpy",
                                                        "mpi4py", "papi", "ScaLAPACK", "SuiteSparse"]

            deps = [dep['name'] for dep in self.cfg.dependencies() if not dep['name'] in depfilter]
            for dep in deps:
                if type(dep) == str:
                    dep = (dep, dep)
                deproot = get_software_root(dep[0])
                if deproot:
                    if (LooseVersion(self.version) >= LooseVersion("3.5")) and (dep[1] == "SCOTCH"):
                        withdep = "--with-pt%s" % dep[1].lower()  # --with-ptscotch is the configopt PETSc >= 3.5
                    else:
                        withdep = "--with-%s" % dep[1].lower()
                    self.cfg.update('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

            # SuiteSparse options changed in PETSc 3.5,
            suitesparse = get_software_root('SuiteSparse')
            if suitesparse:
                if LooseVersion(self.version) >= LooseVersion("3.5"):
                    withdep = "--with-suitesparse"
                    # specified order of libs matters!
                    ss_libs = ["UMFPACK", "KLU", "CHOLMOD", "BTF", "CCOLAMD", "COLAMD", "CAMD", "AMD"]

                    suitesparse_inc = [os.path.join(suitesparse, l, "Include")
                                    for l in ss_libs]
                    suitesparse_inc.append(os.path.join(suitesparse, "SuiteSparse_config"))
                    inc_spec = "-include=[%s]" % ','.join(suitesparse_inc)

                    suitesparse_libs = [os.path.join(suitesparse, l, "Lib", "lib%s.a" % l.lower())
                                    for l in ss_libs]
                    suitesparse_libs.append(os.path.join(suitesparse, "SuiteSparse_config", "libsuitesparseconfig.a"))
                    lib_spec = "-lib=[%s]" % ','.join(suitesparse_libs)
                else:
                    # CHOLMOD and UMFPACK are part of SuiteSparse (PETSc < 3.5)
                    withdep = "--with-umfpack"
                    inc_spec = "-include=%s" % os.path.join(suitesparse, "UMFPACK", "Include")
                    # specified order of libs matters!
                    umfpack_libs = [os.path.join(suitesparse, l, "Lib", "lib%s.a" % l.lower())
                                    for l in ["UMFPACK", "CHOLMOD", "COLAMD", "AMD"]]
                    lib_spec = "-lib=[%s]" % ','.join(umfpack_libs)

                self.cfg.update('configopts', ' '.join([withdep + spec for spec in ['=1', inc_spec, lib_spec]]))

            # set PETSC_DIR for configure (env) and build_step
            env.setvar('PETSC_DIR', self.cfg['start_dir'])
            self.cfg.update('buildopts', 'PETSC_DIR=%s' % self.cfg['start_dir'])

            if self.cfg['sourceinstall']:
                # run configure without --prefix (required)
                cmd = "%s ./configure %s" % (self.cfg['preconfigopts'], self.cfg['configopts'])
                (out, _) = run_cmd(cmd, log_all=True, simple=False)
            else:
                out = super(EB_PETSc, self).configure_step()

            # check for errors in configure
            error_regexp = re.compile("ERROR")
            if error_regexp.search(out):
                raise EasyBuildError("Error(s) detected in configure output!")

            if self.cfg['sourceinstall']:
                # figure out PETSC_ARCH setting
                petsc_arch_regex = re.compile("^\s*PETSC_ARCH:\s*(\S+)$", re.M)
                res = petsc_arch_regex.search(out)
                if res:
                    self.petsc_arch = res.group(1)
                    self.cfg.update('buildopts', 'PETSC_ARCH=%s' % self.petsc_arch)
                else:
                    raise EasyBuildError("Failed to determine PETSC_ARCH setting.")

            self.petsc_subdir = '%s-%s' % (self.name.lower(), self.version)

        else:  # old versions (< 3.x)

            self.cfg.update('configopts', '--prefix=%s' % self.installdir)
            self.cfg.update('configopts', '--with-shared=1')

            # additional dependencies
            for dep in ["SCOTCH"]:
                deproot = get_software_root(dep)
                if deproot:
                    withdep = "--with-%s" % dep.lower()
                    self.cfg.update('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

            cmd = "./config/configure.py %s" % self.get_cfg('configopts')
            run_cmd(cmd, log_all=True, simple=True)

        # PETSc > 3.5, make does not accept -j
        if LooseVersion(self.version) >= LooseVersion("3.5"):
            self.cfg['parallel'] = None

    # default make should be fine
    
    def install_step(self):
        """
        Install using make install (for non-source installations), 
        or by symlinking files (old versions, < 3).
        """
        if LooseVersion(self.version) >= LooseVersion("3"):
            if not self.cfg['sourceinstall']:
                super(EB_PETSc, self).install_step()

        else:  # old versions (< 3.x)

            try:
                for f in ['petscconf.h', 'petscconfiginfo.h', 'petscfix.h', 'petscmachineinfo.h']:
                    includedir = os.path.join(self.installdir, 'include')
                    bmakedir = os.path.join(self.installdir, 'bmake', 'linux-gnu-c-opt')
                    os.symlink(os.path.join(bmakedir, f), os.path.join(includedir, f))
            except Exception, err:
                raise EasyBuildError("Something went wrong during symlink creation of file %s: %s", f, err)

    def make_module_req_guess(self):
        """Specify PETSc custom values for PATH, CPATH and LD_LIBRARY_PATH."""

        guesses = super(EB_PETSc, self).make_module_req_guess()

        prefix1 = ''
        prefix2 = ''
        if self.cfg['sourceinstall']:
            prefix1 = self.petsc_subdir
            prefix2 = os.path.join(self.petsc_subdir, self.petsc_arch)

        guesses.update({
            'CPATH': [os.path.join(prefix2, 'include'), os.path.join(prefix1, 'include')],
            'LD_LIBRARY_PATH': [os.path.join(prefix2, 'lib')],
            'PATH': [os.path.join(prefix1, 'bin')],
        })

        return guesses

    def make_module_extra(self):
        """Set PETSc specific environment variables (PETSC_DIR, PETSC_ARCH)."""
        txt = super(EB_PETSc, self).make_module_extra()

        if self.cfg['sourceinstall']:
            txt += self.module_generator.set_environment('PETSC_DIR', os.path.join(self.installdir, self.petsc_subdir))
            txt += self.module_generator.set_environment('PETSC_ARCH', self.petsc_arch)
        else:
            txt += self.module_generator.set_environment('PETSC_DIR', self.installdir)

        return txt

    def sanity_check_step(self):
        """Custom sanity check for PETSc"""

        prefix1 = ''
        prefix2 = ''
        if self.cfg['sourceinstall']:
            prefix1 = self.petsc_subdir
            prefix2 = os.path.join(self.petsc_subdir, self.petsc_arch)

        if self.cfg['shared_libs']:
            libext = get_shared_lib_ext()
        else:
            libext = 'a'

            custom_paths = {
                'files': [os.path.join(prefix2, 'lib', 'libpetsc.%s' % libext)],
                'dirs': [os.path.join(prefix1, 'bin'), os.path.join(prefix1, 'include'),
                         os.path.join(prefix2, 'include')]
            }
            if LooseVersion(self.version) < LooseVersion('3.6'):
                custom_paths['dirs'].append(os.path.join(prefix2, 'conf'))
            else:
                custom_paths['dirs'].append(os.path.join(prefix2, 'lib', 'petsc', 'conf'))

        super(EB_PETSc, self).sanity_check_step(custom_paths=custom_paths)
