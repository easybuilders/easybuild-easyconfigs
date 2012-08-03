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
EasyBuild support for installing (precompiled) software packages which are packaged as a tarball,
implemented as an easyblock
"""

import shutil

from easybuild.framework.application import Application


class Tarball(Application):
    """
    Precompiled software packaged as tarball: 
    - will unpack binary and copy it to the install dir
    """

    def configure(self):
        """
        Dummy configure
        """
        pass

    def make(self):
        """
        Dummy make: nothing to build
        """
        pass

    def make_install(self):

        src=self.getcfg('startfrom')
        # shutil.copytree cannot handle destination dirs that exist already.
        # On the other hand, Python2.4 cannot create entire paths during copytree.
        # Therefore, only the final directory is deleted.
        shutil.rmtree(self.installdir)
        try:
            # self.getcfg('keepsymlinks') is False by default except when explicitly put to True in .eb file
            shutil.copytree(src,self.installdir, symlinks=self.getcfg('keepsymlinks'))
        except:
            self.log.exception("Copying %s to installation dir %s failed"%(src,self.installdir))