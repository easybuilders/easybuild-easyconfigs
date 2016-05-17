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
EasyBuild support for building and installing Doxygen, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Balazs Hajgato (Free University Brussels (VUB))
"""

from distutils.version import LooseVersion
from easybuild.tools.run import run_cmd
from easybuild.easyblocks.generic.cmakemake import CMakeMake

class EB_Doxygen(CMakeMake):
    """Support for building/installing Doxygen"""

    def configure_step(self):
        """Configure build using non-standard configure prefix option (without `=`)
           for versions before 1.8.10. Newer versions use cmake instead of configure"""
        if LooseVersion(self.version) < LooseVersion("1.8.10"):

             cmd = "%s ./configure --prefix %s %s" % (self.cfg['preconfigopts'], self.installdir,
                                                      self.cfg['configopts'])
             run_cmd(cmd, log_all=True, simple=True)
        else:
            super(EB_Doxygen, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Doxygen"""

        custom_paths = {
            'files': ["bin/doxygen"],
            'dirs': []
        }

        super(EB_Doxygen, self).sanity_check_step(custom_paths=custom_paths)
