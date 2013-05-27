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
from easybuild.easyblocks.generic.fortranpythonpackage import FortranPythonPackage
from easybuild.tools.filetools import rmtree2, run_cmd
from easybuild.tools.modules import get_software_root


class EB_numpy(FortranPythonPackage):
    """Support for installing the numpy Python package as part of a Python installation."""

    def __init__(self, *args, **kwargs):
        """Initialize numpy-specific class variables."""
        super(EB_numpy, self).__init__(*args, **kwargs)

        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.installopts = ''
        self.testinstall = True
        self.testcmd = "cd .. && python -c 'import numpy; numpy.test(verbose=2)'"

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
                libs.try_remove(['pthread'])
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
                self.log.error("Building numpy on top of Intel MKL requires a patch to "
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
                self.log.error("CBLAS is required next to ACML to provide a C interface to BLAS, but it's not loaded.")

        if fft:
            extrasiteconfig += "\n[fftw]\nlibraries = %s" % fft

        self.sitecfg = '\n'.join([self.sitecfg, extrasiteconfig])

        self.sitecfg = self.sitecfg % {
            'blas': blas,
            'lapack': lapack,
            'libs': libs,
            'includes': includes,
        }

        super(EB_numpy, self).configure_step()

        # check configuration (for debugging purposes)
        cmd = "python setup.py config"
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Run available numpy unit tests, and more."""
        super(EB_numpy, self).test_step()

        # temporarily install numpy, it doesn't alow to be used straight from the source dir
        tmpdir = tempfile.mkdtemp()
        cmd = "python setup.py install --prefix=%s %s" % (tmpdir, self.installopts)
        run_cmd(cmd, log_all=True, simple=True)

        try:
            pwd = os.getcwd()
            os.chdir(tmpdir)
        except OSError, err:
            self.log.error("Faild to change to %s: %s" % (tmpdir, err))

        # evaluate performance of numpy.dot (3 runs, 3 loops each)
        size = 1000
        max_time_msec = 1000  # 1 second should really do it for a 1000x1000 matrix dot product
        cmd = ' '.join([
            'export PYTHONPATH=%s:$PYTHONPATH &&' % os.path.join(tmpdir, self.pylibdir),
            'python -m timeit -n 3 -r 3',
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
            else:
                self.log.error("Failed to determine time for numpy.dot test run.")

        # make sure we observe decent performance
        if time_msec < max_time_msec:
            self.log.info("Time for %(size)dx%(size)d matrix dot product: %(time)d msec < %(maxtime)d msec => OK" %
                {'size': size, 'time': time_msec, 'maxtime': max_time_msec})
        else:
            self.log.error("Time for %(size)dx%(size)d matrix dot product: %(time)d msec >= %(maxtime)d msec => ERROR" %
                {'size': size, 'time': time_msec, 'maxtime': max_time_msec})

        try:
            os.chdir(pwd)
            rmtree2(tmpdir)
        except OSError, err:
            self.log.error("Failed to change back to %s: %s" % (pwd, err))

    def sanity_check_step(self, *args, **kwargs):
        """Custom sanity check for numpy."""

        custom_paths = {
            'files': [os.path.join(self.pylibdir, 'numpy', '__init__.py')],
            'dirs': [],
        }
        custom_commands = [
            ('python', '-c "import numpy"'),
            ('python', '-c "import numpy.core._dotblas"'),  # _dotblas is required for decent performance of numpy.dot()
        ]

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
