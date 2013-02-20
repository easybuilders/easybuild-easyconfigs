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

        elif get_software_root("ATLAS") and get_software_root("LAPACK"):

            extrasiteconfig = '\n'.join(["[blas_opt]",
                                         "libraries = %(blas)s",
                                         "[lapack_opt]",
                                         "libraries = %(lapack)s",
                                        ])

        else:
            self.log.error("Could not detect BLAS/LAPACK library.")

        libfft = os.getenv('LIBFFT')
        if libfft:
            extrasiteconfig += "\n[fftw]\nlibraries = %s" % libfft.replace(' ', ',')

        self.sitecfg = '\n'.join([self.sitecfg, extrasiteconfig])

        lapack_libs = os.getenv("LIBLAPACK_MT").split(" -l")
        blas_libs = os.getenv("LIBBLAS_MT").split(" -l")

        if get_software_root("IMKL"):
            # with IMKL, get rid of all spaces and use '-Wl:'
            lapack_libs.remove("pthread")
            lapack = ','.join(lapack_libs).replace(' ', ',').replace('Wl,', 'Wl:')
            blas = lapack
        else:
            lapack = ", ".join(lapack_libs)
            blas = ", ".join(blas_libs)

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
