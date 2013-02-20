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
EasyBuild support for software that is configured with CMake, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd


class CMakeMake(ConfigureMake):
    """Support for configuring build with CMake instead of traditional configure script"""

    def configure_step(self, builddir=None):
        """Configure build using cmake"""

        if not builddir:
            builddir = '.'

        compilers = "-DCMAKE_C_FLAGS='%s' -DCMAKE_C_COMPILER='%s' " % (os.getenv('CFLAGS'), 
                                                                       os.getenv('CC'))
        compilers += "-DCMAKE_CXX_FLAGS='%s' -DCMAKE_CXX_COMPILER='%s' " % (os.getenv('CXXFLAGS'), 
                                                                            os.getenv('CXX'))

        compilers += "-DCMAKE_Fortran_FLAGS='%s' -DCMAKE_Fortran_COMPILER='%s' " % (os.getenv('FFLAGS'), 
                                                                                    os.getenv('F90'))

        command = "%s cmake -DCMAKE_INSTALL_PREFIX=%s %s %s %s" % (self.cfg['preconfigopts'],
                                                                   self.installdir,
                                                                   compilers,
                                                                   builddir,
                                                                   self.cfg['configopts']
                                                                   )
        (out, _) = run_cmd(command, log_all=True, simple=False)

        return out
