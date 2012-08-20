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
EasyBuild support for Armadillo, implemented as an easyblock
"""
import os

from easybuild.easyblocks.c.cmake import EB_CMake
from easybuild.tools.modules import get_software_root


class EB_Armadillo(EB_CMake):
    """Support for building Armadillo."""

    def configure(self):
        """Set some extra environment variables before configuring."""

        boost = get_software_root('Boost')
        if not boost:
            self.log.error("Dependency module Boost not loaded?")

        self.updatecfg('configopts', "-DBoost_DIR=%s" % boost)
        self.updatecfg('configopts', "-DBOOST_INCLUDEDIR=%s/include" % boost)
        self.updatecfg('configopts', "-DBoost_DEBUG=ON -DBOOST_ROOT=%s" % boost)

        self.updatecfg('configopts', '-DBLAS_LIBRARY:PATH="%s"' % os.getenv('LIBBLAS'))
        self.updatecfg('configopts', '-DLAPACK_LIBRARY:PATH="%s"' % os.getenv('LIBLAPACK'))

        EB_CMake.configure(self)

    def sanitycheck(self):
        """Custom sanity check for Armadillo."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files':['lib/libarmadillo.so', 'include/armadillo'],
                                             'dirs':['include/armadillo_bits']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        EB_CMake.sanitycheck(self)
