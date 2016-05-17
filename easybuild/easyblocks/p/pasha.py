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
EasyBuild support for building and installing Pasha, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""

import shutil
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_Pasha(ConfigureMake):
    """Support for building and installing Pasha"""

    def configure_step(self):
        """Configure Pasha by setting make options."""

        tbb = get_software_root('TBB')
        if not tbb:
            raise EasyBuildError("TBB module not loaded.")

        self.cfg.update('buildopts', "TBB_DIR=%s/tbb MPI_DIR='' MPI_INC='' " % tbb)
        self.cfg.update('buildopts', 'MPI_CXX="%s" OPM_FLAG="%s"' % (os.getenv('MPICXX'), self.toolchain.get_flag('openmp')))
        self.cfg.update('buildopts', 'MPI_LIB="" MY_CXX="%s" MPICH_IGNORE_CXX_SEEK=1' % os.getenv('CXX'))

    def install_step(self):
        """Install by copying everything from 'bin' subdir in build dir to install dir"""

        srcdir = os.path.join(self.builddir, "%s-%s" % (self.name, self.version), 'bin')
        shutil.copytree(srcdir, os.path.join(self.installdir, 'bin'))

    def sanity_check_step(self):
        """Custom sanity check for Pasha"""

        custom_paths = {
                        'files':["bin/pasha-%s" % x for x in ["kmergen", "pregraph", "graph"]],
                        'dirs':[],
                       }

        super(EB_Pasha, self).sanity_check_step(custom_paths=custom_paths)
