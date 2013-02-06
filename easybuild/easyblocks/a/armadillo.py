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
EasyBuild support for Armadillo, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.tools.modules import get_software_root


class EB_Armadillo(CMakeMake):
    """Support for building Armadillo."""

    def configure_step(self):
        """Set some extra environment variables before configuring."""

        boost = get_software_root('Boost')
        if not boost:
            self.log.error("Dependency module Boost not loaded?")

        self.cfg.update('configopts', "-DBoost_DIR=%s" % boost)
        self.cfg.update('configopts', "-DBOOST_INCLUDEDIR=%s/include" % boost)
        self.cfg.update('configopts', "-DBoost_DEBUG=ON -DBOOST_ROOT=%s" % boost)

        self.cfg.update('configopts', '-DBLAS_LIBRARY:PATH="%s"' % os.getenv('LIBBLAS'))
        self.cfg.update('configopts', '-DLAPACK_LIBRARY:PATH="%s"' % os.getenv('LIBLAPACK'))

        super(EB_Armadillo, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Armadillo."""

        custom_paths = {
                        'files':['lib/libarmadillo.so', 'include/armadillo'],
                        'dirs':['include/armadillo_bits']
                       }

        super(EB_Armadillo, self).sanity_check_step(custom_paths=custom_paths)
