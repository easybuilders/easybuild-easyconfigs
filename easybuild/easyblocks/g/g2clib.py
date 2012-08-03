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
EasyBuild support for building and installing g2clib, implemented as an easyblock
"""

import glob
import os
import shutil

from easybuild.framework.application import Application


class G2clib(Application):
    """Support for building g2clib GRIB2 C library."""

    def configure(self):
        """No configuration needed"""
        pass

    def make(self):
        """Build by supplying required make options, and running make."""

        if not os.getenv('SOFTROOTJASPER'):
            self.log.error("JasPer module not loaded?")

        # beware: g2clib uses INC, while g2lib uses INCDIR !
        makeopts = 'CC="%s" FC="%s" INC="-I%s/include"' % (os.getenv('CC'),
                                                           os.getenv('F90'),
                                                           os.getenv('SOFTROOTJASPER'))
        self.updatecfg('makeopts', makeopts)

        Application.make(self)

    def make_install(self):
        """Install by copying library and header files to install directory."""

        try:
            # copy library
            targetdir = os.path.join(self.installdir, "lib")
            os.mkdir(targetdir)
            fn = "libgrib2c.a"
            shutil.copyfile(os.path.join(self.getcfg('startfrom'), fn),
                            os.path.join(targetdir, fn))

            # copy header files
            targetdir = os.path.join(self.installdir, "include")
            os.mkdir(targetdir)
            for fn in glob.glob('*.h'):
                shutil.copyfile(os.path.join(self.getcfg('startfrom'), fn),
                                os.path.join(targetdir, fn))

        except OSError, err:
            self.log.error("Failed to copy files to install dir: %s" % err)

    def sanitycheck(self):
        """Custom sanity check for g2clib."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["lib/libgrib2c.a"],
                                            'dirs':["include"]
                                            })

        Application.sanitycheck(self)
