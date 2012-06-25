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
from easybuild.tools.filetools import mkdir

class METIS(Application):
    """Support for building METIS."""

    def configure(self, *args, **kwargs):
        pass

    def make_install(self):
        """Manually copy the required files to the right place.
        
        And create symlinks where expected by other applications
        (in Lib instead of lib)"""
        libdir = os.path.join(self.installdir, 'lib')
        mkdir(libdir)

        includedir = os.path.join(self.installdir, 'include')
        mkdir(includedir)

        # copy libraries
        try:
            src = os.path.join(self.getcfg('startfrom'), 'libmetis.a')
            dst = os.path.join(libdir, 'libmetis.a')
            shutil.copy2(src, dst)
        except OSError, err:
            self.log.error("Copying file libmetis.a to lib dir failed: %s" % err)

        # copy include files
        try:
            for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                src = os.path.join(self.getcfg('startfrom'), 'Lib', f)
                dst = os.path.join(includedir, f)
                shutil.copy2(src, dst)
                os.chmod(dst, 0755)
        except OSError, err:
            self.log.error("Copying file metis.h to include dir failed: %s" % err)

        # Other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and header files in the Lib directory (capital L). The following symlinks are hence created.
        try:
            Libdir = os.path.join(self.installdir, 'Lib')
            os.symlink(libdir, Libdir)
            for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                os.symlink(os.path.join(includedir, file), os.path.join(libdir, f))
        except OSError, err:
            self.log.error("Something went wrong during symlink creation: %s" % err)
