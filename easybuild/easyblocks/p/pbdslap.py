##
# Copyright 2015 Ghent University
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
EasyBuild support for building and installing pbdSLAP, implemented as an easyblock

@author: Ewan Higgs (Ghent University)
"""

from easybuild.easyblocks.generic.rpackage import RPackage

class EB_pbdSLAP(RPackage):
    """Support for building/installing pbdSLAP."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for pbdSLAP."""
        super(EB_pbdSLAP, self).__init__(*args, **kwargs)
        self.configurevars.append("EXT_LDFLAGS='$LIBSCALAPACK'")
