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

from easybuild.easyblocks.generic.fortranpythonpackage import FortranPythonPackage
from easybuild.tools.filetools import rmtree2
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

        if get_software_root("IMKL"):

            extrasiteconfig = '\n'.join([
                                         "[mkl]",
                                         "lapack_libs = %(lapack)s",
                                         "mkl_libs = %(blas)s",
                                        ])

        elif get_software_root("ATLAS"):
            extrasiteconfig = '\n'.join(["[atlas]",
                                         "atlas_libs = %(lapack)s",
                                        ])
        else:
            extrasiteconfig = '\n'.join(["[blas]",
                                         "blas_libs = %(blas)s",
                                         "[lapack]",
                                         "lapack_libs = %(lapack)s",
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

            blas = ', '.join([x for x in self.toolchain.get_variable('LIBBLAS_MT', typ=list) if x != "pthread"])
            lapack = ', '.join([x for x in self.toolchain.get_variable('LIBLAPACK_MT', typ=list) if x != "pthread"])
            fft = ', '.join(self.toolchain.get_variable('LIBFFT', typ=list))

        if fft:
            extrasiteconfig += "\n[fftw]\nlibraries = %s" % fft

        self.sitecfg = '\n'.join([self.sitecfg, extrasiteconfig])

        self.sitecfg = self.sitecfg % {
                                       'lapack': lapack,
                                       'blas': blas,
                                       'libs': ':'.join(self.toolchain.get_variable('LDFLAGS', typ=list)),
                                       'includes': ':'.join(self.toolchain.get_variable('CPPFLAGS', typ=list))
                                      }

        super(EB_numpy, self).configure_step()

    def install_step(self):
        """Install numpy and remove numpy build dir, so scipy doesn't find it by accident."""
        super(EB_numpy, self).install_step()

        builddir = os.path.join(self.builddir, "numpy")
        if os.path.isdir(builddir):
            rmtree2(builddir)
        else:
            self.log.debug("build dir %s already clean" % builddir)
