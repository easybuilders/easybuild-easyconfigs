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
"""
EasyBuild support for building and installing Pasha, implemented as an easyblock
"""

import shutil
import os

from easybuild.framework.application import Application
from easybuild.tools.modules import get_software_root


class EB_Pasha(Application):
    """Support for building and installing Pasha"""

    def configure(self):
        """Configure Pasha by setting make options."""

        tbb = get_software_root('TBB')
        if not tbb:
            self.log.error("TBB module not loaded.")

        self.updatecfg('makeopts', "TBB_DIR=%s/tbb MPI_DIR='' MPI_INC=''")
        self.updatecfg('makeopts', "MPI_CXX=$MPICXX OPM_FLAG=%s" % (tbb, self.toolkit().get_openmp_flag()))
        self.updatecfg('makeopts', "MPI_LIB='' MY_CXX=$CXX MPICH_IGNORE_CXX_SEEK=1")

    def make_install(self):
        """Install by copying everything from 'bin' subdir in build dir to install dir"""

        srcdir = os.path.join(self.builddir, "%s-%s" % (self.name(), self.version()), 'bin')
        shutil.copytree(srcdir, os.path.join(self.installdir, 'bin'))

    def sanitycheck(self):
        """Custom sanity check for Pasha"""
        self.setcfg('sanityCheckPaths', {
                                         'files':["bin/pasha-%s" % x for x in ["kmergen",
                                                                               "pregraph",
                                                                               "graph"]],
                                        'dirs':[""],
                                        })

