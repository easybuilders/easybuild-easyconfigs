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
EasyBuild support for building and installing the Bioconductor R library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""
from easybuild.easyblocks.generic.rpackage import RPackage
from easybuild.tools.build_log import EasyBuildError


class EB_Bioconductor(RPackage):
    """
    The Bioconductor package extends RPackage to use a different source
    And using the biocLite package to do the installation.
    """
    def make_cmdline_cmd(self):
        """Create a command line to install an R library."""
        raise EasyBuildError("Don't know how to install a specific version of a Bioconductor package.")

    def make_r_cmd(self):
        """Create a command to run in R to install an R library."""
        name = self.ext['name']
        self.log.debug("Installing Bioconductor package %s." % name)

        r_cmd = '\n'.join([
            'source("http://bioconductor.org/biocLite.R")',
            'biocLite("%s")' % name,
        ])
        cmd = "R -q --no-save"

        return cmd, r_cmd
