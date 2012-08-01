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
import shutil
import glob
from easybuild.easyblocks.i.intelbase import IntelBase

class Tbb(IntelBase):
    """
    EasyBlock for tbb, threading building blocks
    """

    def make_install(self):
        """overwrite make_install to add extra symlinks"""
        IntelBase.make_install(self)

        # save libdir
        os.chdir(self.installdir)
        libglob = 'tbb/libs/intel64/cc*libc*_kernel*'
        libs = glob.glob(libglob)
        if len(libs):
            libdir = libs[-1] # take the last one, should be ordered by cc version.
        else:
            self.log.error("No libs found using %s in %s" % (libglob, self.installdir))
        self.libdir = libdir


        self.libpath = "%s/tbb/libs/intel64/%s/" % (self.installdir, libdir)
        # applications go looking into tbb/lib so we move what's in there to libs
        # and symlink the right lib from /tbb/libs/intel64/... to lib
        installibpath = os.path.join(self.installdir, 'tbb', 'lib')
        shutil.move(installibpath, os.path.join(self.installdir, 'tbb', 'libs'))
        os.symlink(self.libpath, installibpath)


    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':[],
                                            'dirs':["tbb/bin", "tbb/lib/", "tbb/libs/"]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        IntelBase.sanitycheck(self)

    def make_module_extra(self):
        """Add correct path to lib to LD_LIBRARY_PATH. and intel license file"""

        txt = IntelBase.make_module_extra(self)
        # since we have symlinked it we could also use $SOFTROOTTBB/tbb/lib here
        txt += "prepend-path\t%s\t\t%s\n" % ('LD_LIBRARY_PATH', self.libpath)

        return txt
