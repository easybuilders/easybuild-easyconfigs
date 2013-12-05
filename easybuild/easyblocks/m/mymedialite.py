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
EasyBuild support for MyMediaLite, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd

class EB_MyMediaLite(EasyBlock):
    """Support for building/installing MyMediaLite."""

    def configure_step(self):
        """Custom configure step for MyMediaLite, using "make CONFIGURE_OPTIONS='...' configure"."""

        cmd = "make CONFIGURE_OPTIONS='--prefix=%s' configure" % self.installdir
        run_cmd(cmd, log_all=True, simple=True)
        
    def build_step(self):
        """Custom build step for MyMediaLite, using 'make all' in 'src' directory."""

        cmd = "cd src && make all && cd .."
        run_cmd(cmd, log_all=True, simple=True)               
        
