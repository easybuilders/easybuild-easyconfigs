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
EasyBuild support for building and installing xml R, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.rpackage import RPackage
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_XML(RPackage):
    """Support for installing the XML R package."""

    def install_R_package(self, cmd, inp=None):
        """Customized install procedure for XML R package, add zlib lib path to LIBS."""

        libs = os.getenv('LIBS', '')
        zlib = get_software_root('zlib')

        if not zlib:
            raise EasyBuildError("zlib module not loaded (required)")

        env.setvar('LIBS', "%s -L%s" % (libs, os.path.join(zlib, 'lib')))

        super(EB_XML, self).install_R_package(cmd, inp)
