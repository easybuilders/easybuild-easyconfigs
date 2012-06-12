##
# Copyright 2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
"""Easyblock for basemap"""

import os
from easybuild.easyblocks.p.pythonpackagemodule import PythonPackageModule
from easybuild.tools.filetools import run_cmd

class Basemap(PythonPackageModule):
    """install the pytables package"""

    def make(self):
        """This uses python setup.py build to build python packages"""
        cmd = "export GEOS_DIR=$SOFTROOTGEOS; python setup.py build"

        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """Uses python setpu.py install to install to a custom path"""
        cmd = "export GEOS_DIR=$SOFTROOTGEOS; python setup.py install --prefix=%s %s" % (self.installdir, self.getcfg('installopts'))
        run_cmd(cmd, log_all=True, simple=True)

