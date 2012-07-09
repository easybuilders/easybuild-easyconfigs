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
from easybuild.framework.application import Application

class G2lib(Application):
    """Support for building g2clib GRIB2 library."""

    def configure(self):
        """No configuration needed"""
        pass

    def make(self):
        """Build by supplying required make options, and running make."""

        if not os.getenv('SOFTROOTJASPER'):
            self.log.error("JasPer module not loaded?")

        makeopts = 'CC="%s" FC="%s" INCDIR="-I%s/include"' % (os.getenv('CC'),
                                                              os.getenv('F90'),
                                                              os.getenv('SOFTROOTJASPER'))
        self.updatecfg('makeopts', makeopts)

        Application.make(self)

    def make_install(self):
        """Install by copying generated library to install directory."""

        try:
            targetdir = os.path.join(self.installdir, "lib")
            os.mkdir(targetdir)
            fn = "libg2.a"
            shutil.copyfile(os.path.join(self.getcfg('startfrom'), fn),
                            os.path.join(targetdir, fn))
        except OSError, err:
            self.log.error("Failed to copy files to install dir: %s" % err)

    def sanitycheck(self):
        """Custom sanity check for g2lib."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["lib/libg2.a"],
                                            'dirs':[]
                                            })

        Application.sanitycheck(self)
