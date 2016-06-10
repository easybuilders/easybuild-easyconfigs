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
EasyBuild support for building and installing numpy, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import re
import tempfile

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.fortranpythonpackage import FortranPythonPackage
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import rmtree2
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from distutils.version import LooseVersion


class EB_numpy(FortranPythonPackage):
    """Support for installing the numpy Python package as part of a Python installation."""

    @staticmethod
    def extra_options():
        """Easyconfig parameters specific to numpy."""
        extra_vars = ({
            'blas_test_time_limit': [500, "Time limit (in ms) for 1000x1000 matrix dot product BLAS test", CUSTOM],
        })
        return FortranPythonPackage.extra_options(extra_vars=extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize numpy-specific class variables."""
        super(EB_numpy, self).__init__(*args, **kwargs)

        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.installopts = ''
        self.testinstall = True
        self.testcmd = "cd .. && %(python)s -c 'import numpy; numpy.test(verbose=2)'"

    def configure_step(self):
        """Configure numpy build by composing site.cfg contents."""

        # see e.g. https://github.com/numpy/numpy/pull/2809/files
        self.sitecfg = '\n'.join([
            "[DEFAULT]",
            "library_dirs = %(libs)s",
            "include_dirs= %(includes)s",
            "search_static_first=True",
        ])

        if get_software_root("imkl"):

            if self.toolchain.comp_family() == toolchain.GCC:
                # see https://software.intel.com/en-us/articles/numpyscipy-with-intel-mkl,
                # section Building with GNU Compiler chain
                extrasiteconfig = '\n'.join([
                    "[mkl]",
                    "lapack_libs = ",
                    "mkl_libs = mkl_rt",
                ])
            else:
                extrasiteconfig = '\n'.join([
                    "[mkl]",
                    "lapack_libs = %(lapack)s",
                    "mkl_libs = %(blas)s",
                ])

        else:
            # [atlas] the only real alternative, even for non-ATLAS BLAS libs (e.g., OpenBLAS, ACML, ...)
            # using only the [blas] and [lapack] sections results in sub-optimal builds that don't provide _dotblas.so;
            # it does require a CBLAS interface to be available for the BLAS library being used
            # e.g. for ACML, the CBLAS module providing a C interface needs to be used
            extrasiteconfig = '\n'.join([
                "[atlas]",
                "atlas_libs = %(lapack)s",
                "[lapack]",
                "lapack_libs = %(lapack)s",  # required by scipy, that uses numpy's site.cfg
            ])

        blas = None
        lapack = None
        fft = None

        if get_software_root("imkl"):
            # with IMKL, no spaces and use '-Wl:'
            # redefine 'Wl,' to 'Wl:' so that the patch file can do its job
            def get_libs_for_mkl(varname):
                """Get list of libraries as required for MKL patch file."""
                libs = self.toolchain.variables['LIB%s' % varname].copy()
                libs.try_remove(['pthread', 'dl'])
                tweaks = {
                    'prefix': '',
                    'prefix_begin_end': '-Wl:',
                    'separator': ',',
                    'separator_begin_end': ',',
                }
                libs.try_function_on_element('change', kwargs=tweaks)
                libs.SEPARATOR = ','
                return str(libs)  # str causes list concatenation and adding prefixes & separators

            blas = get_libs_for_mkl('BLAS_MT')
            lapack = get_libs_for_mkl('LAPACK_MT')
            fft = get_libs_for_mkl('FFT')

            # make sure the patch file is there
            # we check for a typical characteristic of a patch file that cooperates with the above
            # not fool-proof, but better than enforcing a particular patch filename
            patch_found = False
            patch_wl_regex = re.compile(r"replace\(':',\s*','\)")
            for patch in self.patches:
                # patches are either strings (extension) or dicts (easyblock)
                if isinstance(patch, dict):
                    patch = patch['path']
                if patch_wl_regex.search(open(patch, 'r').read()):
                    patch_found = True
                    break
            if not patch_found:
                raise EasyBuildError("Building numpy on top of Intel MKL requires a patch to "
                                     "handle -Wl linker flags correctly, which doesn't seem to be there.")

        else:
            # unless Intel MKL is used, $ATLAS should be set to take full control,
            # and to make sure a fully optimized version is built, including _dotblas.so
            # which is critical for decent performance of the numpy.dot (matrix dot product) function!
            env.setvar('ATLAS', '1')

            lapack = ', '.join([x for x in self.toolchain.get_variable('LIBLAPACK_MT', typ=list) if x != "pthread"])
            fft = ', '.join(self.toolchain.get_variable('LIBFFT', typ=list))

        libs = ':'.join(self.toolchain.get_variable('LDFLAGS', typ=list))
        includes = ':'.join(self.toolchain.get_variable('CPPFLAGS', typ=list))

        # CBLAS is required for ACML, because it doesn't offer a C interface to BLAS
        if get_software_root('ACML'):
            cblasroot = get_software_root('CBLAS')
            if cblasroot:
                lapack = ', '.join([lapack, "cblas"])
                cblaslib = os.path.join(cblasroot, 'lib')
                # with numpy as extension, CBLAS might not be included in LDFLAGS because it's not part of a toolchain
                if not cblaslib in libs:
                    libs = ':'.join([libs, cblaslib])
            else:
                raise EasyBuildError("CBLAS is required next to ACML to provide a C interface to BLAS, "
                                     "but it's not loaded.")

        if fft:
            extrasiteconfig += "\n[fftw]\nlibraries = %s" % fft

        suitesparseroot = get_software_root('SuiteSparse')
        if suitesparseroot:
            amddir = os.path.join(suitesparseroot, 'AMD')
            umfpackdir = os.path.join(suitesparseroot, 'UMFPACK')

            if not os.path.exists(amddir) or not os.path.exists(umfpackdir):
                raise EasyBuildError("Expected SuiteSparse subdirectories are not both there: %s, %s",
                                     amddir, umfpackdir)
            else:
                extrasiteconfig += '\n'.join([
                    "[amd]",
                    "library_dirs = %s" % os.path.join(amddir, 'Lib'),
                    "include_dirs = %s" % os.path.join(amddir, 'Include'),
                    "amd_libs = amd",
                    "[umfpack]",
                    "library_dirs = %s" % os.path.join(umfpackdir, 'Lib'),
                    "include_dirs = %s" % os.path.join(umfpackdir, 'Include'),
                    "umfpack_libs = umfpack",
                ])

        self.sitecfg = '\n'.join([self.sitecfg, extrasiteconfig])

        self.sitecfg = self.sitecfg % {
            'blas': blas,
            'lapack': lapack,
            'libs': libs,
            'includes': includes,
        }

        super(EB_numpy, self).configure_step()

        # check configuration (for debugging purposes)
        cmd = "%s setup.py config" % self.python_cmd
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Run available numpy unit tests, and more."""
        super(EB_numpy, self).test_step()

        # temporarily install numpy, it doesn't alow to be used straight from the source dir
        tmpdir = tempfile.mkdtemp()
        cmd = "%s setup.py install --prefix=%s %s" % (self.python_cmd, tmpdir, self.installopts)
        run_cmd(cmd, log_all=True, simple=True, verbose=False)

        try:
            pwd = os.getcwd()
            os.chdir(tmpdir)
        except OSError, err:
            raise EasyBuildError("Faild to change to %s: %s", tmpdir, err)

        # evaluate performance of numpy.dot (3 runs, 3 loops each)
        size = 1000
        cmd = ' '.join([
            'export PYTHONPATH=%s:$PYTHONPATH &&' % os.path.join(tmpdir, self.pylibdir),
            '%s -m timeit -n 3 -r 3' % self.python_cmd,
            '-s "import numpy; x = numpy.random.random((%(size)d, %(size)d))"' % {'size': size},
            '"numpy.dot(x, x.T)"',
        ])
        (out, ec) = run_cmd(cmd, simple=False)
        self.log.debug("Test output: %s" % out)

        # fetch result
        time_msec = None
        msec_re = re.compile("\d+ loops, best of \d+: (?P<time>[0-9.]+) msec per loop")
        res = msec_re.search(out)
        if res:
            time_msec = float(res.group('time'))
        else:
            sec_re = re.compile("\d+ loops, best of \d+: (?P<time>[0-9.]+) sec per loop")
            res = sec_re.search(out)
            if res:
                time_msec = 1000 * float(res.group('time'))
            elif self.dry_run:
                # use fake value during dry run
                time_msec = 123
                self.log.warning("Using fake value for time required for %dx%d matrix dot product under dry run: %s",
                                 size, size, time_msec)
            else:
                raise EasyBuildError("Failed to determine time for numpy.dot test run.")

        # make sure we observe decent performance
        if time_msec < self.cfg['blas_test_time_limit']:
            self.log.info("Time for %dx%d matrix dot product: %d msec < %d msec => OK",
                          size, size, time_msec, self.cfg['blas_test_time_limit'])
        else:
            raise EasyBuildError("Time for %dx%d matrix dot product: %d msec >= %d msec => ERROR",
                                 size, size, time_msec, self.cfg['blas_test_time_limit'])
        try:
            os.chdir(pwd)
            rmtree2(tmpdir)
        except OSError, err:
            raise EasyBuildError("Failed to change back to %s: %s", pwd, err)

    def sanity_check_step(self, *args, **kwargs):
        """Custom sanity check for numpy."""

        custom_paths = {
            'files': [os.path.join(self.pylibdir, 'numpy', '__init__.py')],
            'dirs': [],
        }
        custom_commands = [
            ('python', '-c "import numpy"'),
        ]
        if LooseVersion(self.version) >= LooseVersion("1.10"):
            # generic check to see whether numpy v1.10.x and up was built against a CBLAS-enabled library
            # cfr. https://github.com/numpy/numpy/issues/6675#issuecomment-162601149
            blas_check_pytxt = '; '.join([
                "import sys",
                "import numpy",
                "blas_ok = 'HAVE_CBLAS' in dict(numpy.__config__.blas_opt_info['define_macros'])",
                "sys.exit((1, 0)[blas_ok])",
            ])
            custom_commands.append(('python', '-c "%s"' % blas_check_pytxt))
        else:
            # _dotblas is required for decent performance of numpy.dot(), but only there in numpy 1.9.x and older
            custom_commands.append (('python', '-c "import numpy.core._dotblas"'))

        # make sure the installation path is in $PYTHONPATH so the sanity check commands can work
        pythonpath = os.environ.get('PYTHONPATH', '')
        os.environ['PYTHONPATH'] = ':'.join([self.pylibdir, pythonpath])

        return super(EB_numpy, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def install_step(self):
        """Install numpy and remove numpy build dir, so scipy doesn't find it by accident."""
        super(EB_numpy, self).install_step()

        builddir = os.path.join(self.builddir, "numpy")
        if os.path.isdir(builddir):
            rmtree2(builddir)
        else:
            self.log.debug("build dir %s already clean" % builddir)
