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
EasyBuild support for PyZMQ, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
"""

from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.modules import get_software_root


class EB_PyZMQ(PythonPackage):
    """Support for installing the PyZMQ Python package."""

    def configure_step(self):
        """Generate the setup.cfg file for the ZeroMQ libs/includes"""
        self.sitecfgfn = 'setup.cfg'
        root_zmq = get_software_root("ZeroMQ")
        if root_zmq:
            self.log.info("External ZeroMQ found with root %s" % root_zmq)
            self.sitecfg = """[build_ext]
library_dirs = %(zmq)s/lib
include_dirs = %(zmq)s/include
""" % { 'zmq': root_zmq }
        else:
            self.log.info("External ZeroMQ not found, PyZMQ will (try to) use shipped ZeroMQ.")

        super(EB_PyZMQ, self).configure_step()

