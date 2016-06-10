##
# Copyright 2013 Ghent University
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
EasyBuild support for DL_POLY Classic, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""
import os
import shutil

from easybuild.tools.filetools import copytree
from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_DL_underscore_POLY_underscore_Classic(ConfigureMake):
    """Support for building and installing DL_POLY Classic."""

    def configure_step(self):
        """Copy the makefile to the source directory and use MPIF90 to do a parrallel build"""
        shutil.copy("build/MakePAR", "source/Makefile")
        os.chdir("source")
        self.cfg.update('buildopts', 'LD="$MPIF90 -o" FC="$MPIF90 -c" par')

    def install_step(self):
        """Copy the executables to the installation directory"""
        self.log.debug("copying %s/execute to %s, (from %s)", self.cfg['start_dir'], self.installdir, os.getcwd())
        # create a /bin, this way we also get the PATH to be set correctly automatically
        bin_path = os.path.join(self.installdir, "bin")
        install_path = os.path.join(self.cfg['start_dir'], 'execute')
        copytree(install_path, bin_path)
