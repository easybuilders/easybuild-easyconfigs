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
EasyBuild support for installing the Intel Fortran compiler suite, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Ward Poelmans (Ghent University)
"""

import os
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase
from easybuild.easyblocks.icc import EB_icc  #@UnresolvedImport
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_ifort(EB_icc, IntelBase):
    """
    Class that can be used to install ifort
    - tested with 11.1.046
    -- will fail for all older versions (due to newer silent installer)
    """

    def sanity_check_step(self):
        """Custom sanity check paths for ifort."""
        shlib_ext = get_shared_lib_ext()

        binprefix = 'bin/intel64'
        libprefix = 'lib/intel64'
        if LooseVersion(self.version) >= LooseVersion('2011'):
            if LooseVersion(self.version) <= LooseVersion('2011.3.174'):
                binprefix = 'bin'
            elif LooseVersion(self.version) >= LooseVersion('2013_sp1'):
                binprefix = 'bin'
            else:
                libprefix = 'compiler/lib/intel64'

        bins = ['ifort']
        if LooseVersion(self.version) < LooseVersion('2013'):
            # idb is not shipped with ifort anymore in 2013.x versions (it is with icc though)
            bins.append('idb')

        libs = ['ifcore.a', 'ifcore.%s' % shlib_ext, 'iomp5.a', 'iomp5.%s' % shlib_ext]
        custom_paths = {
            'files': [os.path.join(binprefix, x) for x in bins] + [os.path.join(libprefix, 'lib%s' % l) for l in libs],
            'dirs': [],
        }
        IntelBase.sanity_check_step(self, custom_paths=custom_paths)
