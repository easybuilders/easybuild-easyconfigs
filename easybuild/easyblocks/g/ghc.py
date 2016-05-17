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
EasyBuild support for binary GHC packages, see http://haskell.org/ghc

@author: Andy Georges (Ghent University)
"""
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_GHC(ConfigureMake):
    """
    Support for building and installing applications with configure/make/make install
    """

    def build_step(self, verbose=False):
        """
        Support for a binary 6.12.x installation. Starting there,
        later GHC versions are build from source and thus require
        the build step.
        """
        if LooseVersion(self.version) < LooseVersion("7.0"):
            pass
        else:
            super(EB_GHC, self).build_step(verbose=verbose)

