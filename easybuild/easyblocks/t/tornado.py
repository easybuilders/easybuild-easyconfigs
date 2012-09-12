##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for installing the Intel Threading Building Blocks (TBB) library, implemented as an easyblock
"""

import os
import shutil
import glob

from easybuild.easyblocks.packedbinary import EB_PackedBinary


class EB_Tornado(EB_PackedBinary):
    """EasyBlock for Tornado"""

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {
                                             'files':[],
                                             'dirs':["Tornado/bin/linux/", "ThirdParty/bin/linux/"]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        return EB_PackedBinary.sanitycheck(self)

    def make_module_extra(self):
        """Add correct path to lib to LD_LIBRARY_PATH."""

        txt = EB_PackedBinary.make_module_extra(self)
        txt += "prepend-path\t%s\t\t%s\n" % ('LD_LIBRARY_PATH', "$root/Tornado/bin/linux/" )
        txt += "prepend-path\t%s\t\t%s\n" % ('LD_LIBRARY_PATH', "$root/ThirdParty/bin/linux/" )
        txt += "prepend-path\t%s\t\t%s\n" % ('PATH', "$root/Tornado/bin/linux/" )
        txt += "setenv\t%s\t\t%s\n" % ('TORNADO_ROOT_PATH', "$root" )
        txt += "setenv\t%s\t\t%s\n" % ('TORNADO_DATA_PATH', "$root/Data/WEST" )

        return txt
