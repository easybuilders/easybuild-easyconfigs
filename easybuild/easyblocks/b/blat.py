##
# Copyright 2009-2016 the Cyprus Institute
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
EasyBuild support for BLAT

@author: Andreas Panteli (The Cyprus Institute)
@author: Thekla Loizou (The Cyprus Institute)
@author: George Tsouloupas (The Cyprus Institute)
"""
import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.tools.filetools import mkdir


class EB_BLAT(MakeCp):
    """Support for building and installing BLAT."""

    def configure_step(self):
        """Configure build: just create a 'bin' directory."""
        mkdir("bin")

    def build_step(self, verbose=False):
        """Build BLAT using make and the appropriate options (e.g. BINDIR=)."""
        self.cfg.update('prebuildopts', "MACHTYPE=x86_64")
        bindir = os.path.join(os.getcwd(), "bin")
        self.cfg.update('buildopts', "BINDIR=%s" % bindir)

        return super(EB_BLAT, self).build_step(verbose=verbose)
