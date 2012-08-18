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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild. If not, see <http://www.gnu.org/licenses/>.
##
"""
General EasyBuild support for software with a binary installer
"""

import shutil
import os
import stat

from easybuild.framework.application import Application


class eb_Binary(Application):
    """Support for installing a binary package.
    Just copy it's sources to the installdir"""

    def unpack_src(self):
        """Move all source files to the build directory"""

        self.src[0]['finalpath'] = self.builddir

        # copy source to build dir.
        for source in self.src:
            src = source['path']
            dst = os.path.join(self.builddir, source['name'])
            try:
                shutil.copy2(src, self.builddir)
                os.chmod(dst, stat.S_IRWXU)
            except (OSError, IOError), err:
                self.log.exception("Couldn't copy %s to %s: %s" % (src, self.builddir, err))

    def configure(self):
        """No configuration, this is a binary package"""
        pass

    def make(self):
        """No compilation, this is a binary package"""
        pass

    def make_installdir(self):
        """Do not actually create installdir, copytree in make_install doesn't
        want the destination directory already exist
        But in python < 2.5 the actual path leading up to the directory has to exist."""
        self.make_dir(self.installdir, clean=True, dontcreateinstalldir=True)

    def make_install(self):
        """Copy the unpacked source to the install directory"""
        shutil.copytree(self.getcfg('startfrom'), self.installdir, symlinks=True)

    def make_module_extra(self):
        """Add the install directory to the PATH."""

        txt = Application.make_module_extra(self)
        txt += self.moduleGenerator.prependPaths("PATH", [""])
        self.log.debug("make_module_extra added this: %s" % txt)
        return txt
