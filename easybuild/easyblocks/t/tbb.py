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

import os
from easybuild.easyblocks.i.intelbase import IntelBase

class Tbb(IntelBase):
    """
    EasyBlock for tbb, threading building blocks
    """

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':[],
                                            'dirs':["tbb/bin", "tbb/lib/intel64"]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        IntelBase.sanitycheck(self)

    def make_module_extra(self):
        """Add correct path to lib to LD_LIBRARY_PATH. and intel license file"""

        txt = IntelBase.make_module_extra(self)
        txt += "prepend-path\t%s\t\t$root/%s/%s/lib\n" % \
             ('LD_LIBRARY_PATH', os.environ['ARCHITECTURE'], os.environ['TBB_COMPILER'])

        return txt
