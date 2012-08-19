##
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
EasyBuild support for PETSc, implemented as an easyblock
"""
import os
import re
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolkit as toolkit
from easybuild.framework.application import Application
from easybuild.framework.easyconfig import BUILD, CUSTOM
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_PETSc(Application):
    """Support for building and installing PETSc"""

    def __init__(self, *args, **kwargs):
        """Initialize PETSc specific variables."""
        Application.__init__(self, *args, **kwargs)

        self.petsc_arch = ""
        self.petsc_subdir = ""

    @staticmethod
    def extra_options():
        """Add extra config options specific to PETSc."""
        extra_vars = [
                      ('sourceinstall', [False, "Indicates whether a source installation should be performed (default: False)", CUSTOM]),
                      ('shared_libs', [False, "Build shared libraries (default: False)", CUSTOM]),
                      ('with_papi', [False, "Enable PAPI support (default: False)", CUSTOM]),
                      ('papi_inc', ['/usr/include', "Path for PAPI include files (default: /usr/include)", CUSTOM]),
                      ('papi_lib', ['/usr/lib64/libpapi.so', "Path for PAPI library (default: '/usr/lib64/libpapi.so')", CUSTOM]),
                      ('runtest', ['test', "Make target to test build (default: test)", BUILD])
                     ]
        return Application.extra_options(extra_vars)

    def make_builddir(self):
        """Decide whether or not to build in install dir before creating build dir."""

        if self.getcfg('sourceinstall'):
            self.build_in_installdir = True

        Application.make_builddir(self)

    def configure(self):
        """
        Configure PETSc by setting configure options and running configure script.

        Configure procedure is much more concise for older versions (< v3).
        """

        if LooseVersion(self.version()) >= LooseVersion("3"):

            # compilers
            self.updatecfg('configopts', '--with-cc="%s"' % os.getenv('CC'))
            self.updatecfg('configopts', '--with-cxx="%s" --with-c++-support' % os.getenv('CXX'))
            self.updatecfg('configopts', '--with-fc="%s"' % os.getenv('F90'))

            # compiler flags
            self.updatecfg('configopts', '--with-cflags="%s"' % os.getenv('CFLAGS'))
            self.updatecfg('configopts', '--with-cxxflags="%s"' % os.getenv('CXXFLAGS'))
            self.updatecfg('configopts', '--with-fcflags="%s"' % os.getenv('F90FLAGS'))

            if not self.toolkit().comp_family() == toolkit.GCC:
                self.updatecfg('configopts', '--with-gnu-compilers=0')

            # MPI
            if self.toolkit().opts['usempi']:
                self.updatecfg('configopts', '--with-mpi=1')

            # build options
            self.updatecfg('configopts', '--with-make-np=%s' % self.getcfg('parallel'))
            self.updatecfg('configopts', '--with-shared-libraries=%d' % self.getcfg('shared_libs'))
            self.updatecfg('configopts', '--with-debugging=%d' % self.toolkit().opts['debug'])
            self.updatecfg('configopts', '--with-pic=%d' % self.toolkit().opts['pic'])
            self.updatecfg('configopts', '--with-x=0 --with-windows-graphics=0')

            # PAPI support
            if self.getcfg('with_papi'):
                papi_inc = self.getcfg('papi_inc')
                papi_inc_file = os.path.join(papi_inc, "papi.h")
                papi_lib = self.getcfg('papi_lib')
                if os.path.isfile(papi_inc_file) and os.path.isfile(papi_lib):
                    self.updatecfg('configopts', '--with-papi=1')
                    self.updatecfg('configopts', '--with-papi-include=%s' % papi_inc)
                    self.updatecfg('configopts', '--with-papi-lib=%s' % papi_lib)
                else:
                    self.log.error("PAPI header (%s) and/or lib (%s) not found, " % (papi_inc_file,
                                                                                     papi_lib) + \
                                   "can not enable PAPI support?")

            # Python packages
            if get_software_root('Python'):
                self.updatecfg('configopts', '--with-numpy=1')
                if self.getcfg('shared_libs'):
                    self.updatecfg('configopts', '--with-mpi4py=1')

            # BLACS, FFTW, ScaLAPACK
            for dep in ["BLACS", "FFTW", "ScaLAPACK"]:
                inc = os.getenv('%s_INC_DIR' % dep.upper())
                libdir = os.getenv('%s_LIB_DIR' % dep.upper())
                libs = os.getenv('%s_STATIC_LIBS' % dep.upper())
                if inc and libdir and libs:
                    with_arg = "--with-%s" % dep.lower()
                    self.updatecfg('configopts', '%s=1' % with_arg)
                    self.updatecfg('configopts', '%s-include=%s' % (with_arg, inc))
                    self.updatecfg('configopts', '%s-lib=[%s/%s]' % (with_arg, libdir, libs))
                else:
                    self.log.info("Missing inc/lib info, so not enabling %s support." % dep)

            # BLAS, LAPACK libraries
            bl_libdir = os.getenv('BLAS_LAPACK_LIB_DIR')
            bl_libs = os.getenv('BLAS_LAPACK_STATIC_LIBS')
            if bl_libdir and bl_libs:
                self.updatecfg('configopts', '--with-blas-lapack-lib=[%s/%s]' % (bl_libdir, bl_libs))
            else:
                    self.log.error("One or more environment variables for BLAS/LAPACK not defined?")

            # additional dependencies
            # filter out deps handled seperately
            depfilter = self.cfg.builddependencies() + ["BLACS", "BLAS", "FFTW", "LAPACK", "numpy",
                                                        "mpi4py", "papi", "ScaLAPACK", "SuiteSparse"]
            deps = [dep['name'] for dep in self.cfg.dependencies() if not dep['name'] in depfilter]
            for dep in deps:
                if type(dep) == str:
                    dep = (dep, dep)
                deproot = get_software_root(dep[0])
                if deproot:
                    withdep = "--with-%s" % dep[1].lower()
                    self.updatecfg('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

            # CHOLMOD and UMFPACK are part of SuiteSparse
            suitesparse = get_software_root('SuiteSparse')
            if suitesparse:
                withdep = "--with-umfpack"
                # specified order of libs matters!
                umfpack_libs = [os.path.join(suitesparse, l, "Lib", "lib%s.a" % l.lower())
                                for l in ["UMFPACK", "CHOLMOD", "COLAMD", "AMD"]]

                self.updatecfg('configopts', ' '.join([(withdep+x) for x in [
                                                                             "=1",
                                                                             "-include=%s" % os.path.join(suitesparse, "UMFPACK", "Include"),
                                                                             "-lib=[%s]" % ','.join(umfpack_libs)
                                                                            ]
                                                       ])
                               )

            # set PETSC_DIR for configure (env) and make
            env.set('PETSC_DIR', self.getcfg('startfrom'))
            self.updatecfg('makeopts', 'PETSC_DIR=%s' % self.getcfg('startfrom'))

            if self.getcfg('sourceinstall'):
                # run configure without --prefix (required)
                cmd = "%s ./configure %s" % (self.getcfg('preconfigopts'), self.getcfg('configopts'))
                (out, _) = run_cmd(cmd, log_all=True, simple=False)
            else:
                out = Application.configure(self)

            # check for errors in configure
            error_regexp = re.compile("ERROR")
            if error_regexp.search(out):
                self.log.error("Error(s) detected in configure output!")

            if self.getcfg('sourceinstall'):
                # figure out PETSC_ARCH setting
                petsc_arch_regex = re.compile("^\s*PETSC_ARCH:\s*(\S+)$", re.M)
                res = petsc_arch_regex.search(out)
                if res:
                    self.petsc_arch = res.group(1)
                    self.updatecfg('makeopts', 'PETSC_ARCH=%s' % self.petsc_arch)
                else:
                    self.log.error("Failed to determine PETSC_ARCH setting.")

            self.petsc_subdir = '%s-%s' % (self.name().lower(), self.version())

        else:  # old versions (< 3.x)

            self.updatecfg('configopts', '--prefix=%s' % self.installdir)
            self.updatecfg('configopts', '--with-shared=1')

            # additional dependencies
            for dep in ["SCOTCH"]:
                deproot = get_software_root(dep)
                if deproot:
                    withdep = "--with-%s" % dep.lower()
                    self.updatecfg('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

            cmd = "./config/configure.py %s" % self.get_cfg('configopts')
            run_cmd(cmd, log_all=True, simple=True)

    # default make should be fine

    def make_install(self):
        """
        Install using make install (for non-source installations), 
        or by symlinking files (old versions, < 3).
        """
        if LooseVersion(self.version()) >= LooseVersion("3"):
            if not self.getcfg('sourceinstall'):
                Application.make_install(self)

        else:  # old versions (< 3.x)

            try:
                for f in ['petscconf.h', 'petscconfiginfo.h', 'petscfix.h', 'petscmachineinfo.h']:
                    includedir = os.path.join(self.installdir, 'include')
                    bmakedir = os.path.join(self.installdir, 'bmake', 'linux-gnu-c-opt')
                    os.symlink(os.path.join(bmakedir, f), os.path.join(includedir, f))
            except Exception, err:
                self.log.error("Something went wrong during symlink creation of file %s: %s" % (f, err))

    def make_module_req_guess(self):
        """Specify PETSc custom values for PATH, CPATH and LD_LIBRARY_PATH."""

        guesses = Application.make_module_req_guess(self)

        prefix1 = ""
        prefix2 = ""
        if self.getcfg('sourceinstall'):
            prefix1 = self.petsc_subdir
            prefix2 = os.path.join(self.petsc_subdir, self.petsc_arch)

        guesses.update({
                        'PATH': [os.path.join(prefix1, "bin")],
                        'CPATH': [os.path.join(prefix2, "include"),
                                  os.path.join(prefix1, "include")],
                        'LD_LIBRARY_PATH': [os.path.join(prefix2, "lib")]
                        })

        return guesses

    def make_module_extra(self):
        """Set PETSc specific environment variables (PETSC_DIR, PETSC_ARCH)."""
        txt = Application.make_module_extra(self)

        if self.getcfg('sourceinstall'):
            txt += self.moduleGenerator.setEnvironment('PETSC_DIR', '$root/%s' % self.petsc_subdir)
            txt += self.moduleGenerator.setEnvironment('PETSC_ARCH', self.petsc_arch)

        else:
            txt += self.moduleGenerator.setEnvironment('PETSC_DIR', '$root')

        return txt

    def sanitycheck(self):
        """Custom sanity check for PETSc"""

        if not self.getcfg('sanityCheckPaths'):

            prefix1 = ""
            prefix2 = ""
            if self.getcfg('sourceinstall'):
                prefix1 = self.petsc_subdir
                prefix2 = os.path.join(self.petsc_subdir, self.petsc_arch)

            if self.getcfg('shared_libs'):
                libext = get_shared_lib_ext()
            else:
                libext = "a"

            self.setcfg('sanityCheckPaths', {
                                             'files': [os.path.join(prefix2,
                                                                    "lib",
                                                                    "libpetsc.%s" % libext)
                                                       ],
                                             'dirs': [os.path.join(prefix1, "bin"),
                                                      os.path.join(prefix2, "conf"),
                                                      os.path.join(prefix1, "include"),
                                                      os.path.join(prefix2, "include")]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
