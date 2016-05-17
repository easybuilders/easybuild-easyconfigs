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
General EasyBuild support for installing the Enthought Python Distribution

@author: Jens Timmerman
"""
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.tools.run import run_cmd


class EB_EPD(Binary):
    """Easyblock implementing the build step for EPD,
    this is just running the installer script, with an argument to the installdir
    """

    def install_step(self):
        """Overwrite install_step from Binary"""
        os.chdir(self.builddir)
        if self.cfg['install_cmd'] is None:
            self.cfg['install_cmd'] = "./epd_free-%s-x86_64.sh -b -p %s" % (self.version, self.installdir)
        super(EB_EPD, self).install_step()

