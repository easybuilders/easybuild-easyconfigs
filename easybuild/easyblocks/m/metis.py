##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
from easybuild.framework.application import Application
import os
import shutil
class METIS(Application):

    def configure(self):
        pass

    def make_install(self):
        #TODO: make a general mkdir function
        try:
            self.libdir = os.path.join(self.installdir, 'lib')
            os.mkdir(self.libdir)
            self.log.debug("Succesfully created directory %s" % self.libdir)
        except Exception, err:
            self.log.error("Failed to create directory %s: %s" % (self.libdir, err))

        try:
            self.includedir = os.path.join(self.installdir, 'include')
            os.mkdir(self.includedir)
            self.log.debug("Succesfully created directory %s" % self.includedir)
        except Exception, err:
            self.log.error("Failed to create directory %s: %s" % (self.includedir, err))

        try:
            src = os.path.join(self.getcfg('startfrom'), 'libmetis.a')
            dst = os.path.join(self.libdir, 'libmetis.a')
            shutil.copy2(src, dst)
        except Exception, err:
            self.log.error("Copying file libmetis.a to lib dir failed: %s" % err)

        try:
            for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                src = os.path.join(self.getcfg('startfrom'), 'Lib', f)
                dst = os.path.join(self.includedir, f)
                shutil.copy2(src, dst)
                os.chmod(dst, 0755)
        except Exception, err:
            self.log.error("Copying file metis.h to include dir failed: %s" % err)

        # Other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and headerfiles in the Lib directory (capital L). The following symlinks are hence created.
        try:
            self.Libdir = os.path.join(self.installdir, 'Lib')
            os.symlink(self.libdir, self.Libdir)
            for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                os.symlink(os.path.join(self.includedir, file), os.path.join(self.libdir, f))
        except Exception, err:
            self.log.error("Something went wrong during symlink creation: %s" % err)
