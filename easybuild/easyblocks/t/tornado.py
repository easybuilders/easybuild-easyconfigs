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
EasyBuild support for installing Tornado, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""
import os
from easybuild.easyblocks.generic.packedbinary import PackedBinary

class EB_Tornado(PackedBinary):
    """EasyBlock for Tornado"""

    def sanity_check_step(self):
        """Custom sanity check for Tornado."""
        custom_paths = {
            'files': [],
            'dirs': ["Tornado/bin/linux/", "ThirdParty/bin/linux/"],
        }
        super(EB_Tornado, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add correct path to lib to LD_LIBRARY_PATH."""

        txt = super(EB_Tornado, self).make_module_extra()

        txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', ["Tornado/bin/linux/", "ThirdParty/bin/linux/"])
        txt += self.module_generator.prepend_paths('PATH', ["Tornado/bin/linux/"])
        txt += self.module_generator.set_environment('TORNADO_ROOT_PATH', self.installdir)
        txt += self.module_generator.set_environment('TORNADO_DATA_PATH', os.path.join(self.installdir, 'Data', 'WEST'))

        return txt
