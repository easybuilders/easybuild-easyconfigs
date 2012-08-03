##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
"""
EasyBuild support for building and installing Doxygen, implemented as an easyblock
"""

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd


class Doxygen(Application):
    """Support for building/installing Doxygen"""

    def configure(self):
        """Configure build using non-standard configure script (see prefix option)"""

        cmd = "%s ./configure --prefix %s %s" % (self.getcfg('preconfigopts'), self.installdir,
                                                   self.getcfg('configopts'))
        run_cmd(cmd, log_all=True, simple=True)

    def sanitycheck(self):
        """
        Custom sanity check for Doxygen
        """
        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths',{'files':["bin/doxygen"],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)