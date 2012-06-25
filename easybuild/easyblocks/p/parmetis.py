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

from distutils.version import LooseVersion
from easybuild.easyblocks.m.metis import METIS
from easybuild.tools.filetools import run_cmd, mkdir

class ParMETIS(METIS):
    """Support for building and installing ParMETIS."""

    def configure(self):
        """Configure ParMETIS build.
        For versions of ParMETIS < 4 configure METIS separately
        New versions of ParMETIS include METIS
        
        Run 'cmake' in the build dir to get rid of a 'user friendly' 
        help message that is displayed without this step.
        """
        if LooseVersion(self.version()) < LooseVersion("4"):
            return METIS.configure(self)\

        # tested with 4.0.2, now actually requires cmake to be run first
        # for both parmetis and metis
        self.parmetis_builddir = 'build'
        cmd = 'cd %s && cmake .. %s -DCMAKE_INSTALL_PREFIX="%s" && cd %s' % \
            (self.parmetis_builddir, self.getcfg('configopts'), self.installdir, self.getcfg('startfrom'))
        run_cmd(cmd, log_all=True, simple=True)

    def make(self, verbose=False):
        """Build METIS and ParMETIS using make."""

        paracmd = ''
        if self.getcfg('parallel'):
            paracmd = "-j %s" % self.getcfg('parallel')

        cmd = "%s make %s %s" % (self.getcfg('premakeopts'), paracmd, self.getcfg('makeopts'))

        # run make in build dir as well for recent version
        if LooseVersion(self.version()) >= LooseVersion("4"):
            cmd = "cd %s && %s && cd %s " % (self.parmetis_builddir, cmd, self.getcfg('startfrom'))

        run_cmd(cmd, log_all=True, simple=True, log_output=verbose)

    def make_install(self):
        """Install by copying files over to the right places

        Also create symlinks where expected by other packages (Lib directory)
        """
        includedir = os.path.join(self.installdir, 'include')
        libdir = os.path.join(self.installdir, 'lib')

        if LooseVersion(self.version()) >= LooseVersion("4"):
            #i ncludedir etc changed in v4, use a normal makeinstall
            cmd = "cd %s && make install %s && cd %s" % (self.parmetis_builddir, 
                                                         self.getcfg('installopts'),
                                                         self.getcfg('startfrom'))
            run_cmd(cmd, log_all=True, simple=True)

            # libraries
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build/libmetis/libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

            # include files
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build/metis/include/metis.h')
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

        else:

            mkdir(libdir)
            mkdir(includedir)

            # libraries
            try:
                for fil in ['libmetis.a', 'libparmetis.a']:
                    src = os.path.join(self.getcfg('startfrom'), fil)
                    dst = os.path.join(libdir, fil)
                    shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

            # include files
            try:
                src = os.path.join(self.getcfg('startfrom'), 'parmetis.h')
                dst = os.path.join(includedir, 'parmetis.h')
                shutil.copy2(src, dst)
                # Some applications (SuiteSparse) can only use METIS (not ParMETIS), but header files are the same
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

        # Other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and header files in the Lib directory (capital L). The following symlink are hence created.
        try:
            llibdir = os.path.join(self.installdir, 'Lib')
            os.symlink(libdir, llibdir)
            os.symlink(os.path.join(includedir, 'metis.h'), os.path.join(libdir, 'metis.h'))
            os.symlink(os.path.join(includedir, 'parmetis.h'),
                       os.path.join(libdir, 'parmetis.h'))
        except OSError, err:
            self.log.error("Something went wrong during symlink creation: %s" % err)
