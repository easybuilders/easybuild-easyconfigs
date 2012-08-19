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
EasyBuild support for ParMETIS, implemented as an easyblock
"""
import os
import shutil
from distutils.version import LooseVersion

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, mkdir


class EB_ParMETIS(Application):
    """Support for building and installing ParMETIS."""

    def configure(self):
        """Configure ParMETIS build.
        For versions of ParMETIS < 4 , METIS is a seperate build
        New versions of ParMETIS include METIS
        
        Run 'cmake' in the build dir to get rid of a 'user friendly' 
        help message that is displayed without this step.
        """
        if LooseVersion(self.version()) >= LooseVersion("4"):
            # tested with 4.0.2, now actually requires cmake to be run first
            # for both parmetis and metis

            self.updatecfg('configopts', '-DMETIS_PATH=../metis -DGKLIB_PATH=../metis/GKlib')

            self.updatecfg('configopts', '-DOPENMP="%s"' % self.toolkit().get_openmp_flag())

            if self.toolkit().opts['usempi']:
                self.updatecfg('configopts', '-DCMAKE_C_COMPILER="$MPICC"')

            if self.toolkit().opts['pic']:
                self.updatecfg('configopts', '-DCMAKE_C_FLAGS="-fPIC"')

            self.parmetis_builddir = 'build'
            try:
                os.chdir(self.parmetis_builddir)
                cmd = 'cmake .. %s -DCMAKE_INSTALL_PREFIX="%s"' % (self.getcfg('configopts'),
                                                                   self.installdir)
                run_cmd(cmd, log_all=True, simple=True)
                os.chdir(self.getcfg('startfrom'))
            except OSError, err:
                self.log.error("Running cmake in %s failed: %s" % (self.parmetis_builddir, err))

    def make(self, verbose=False):
        """Build ParMETIS (and METIS) using make."""

        paracmd = ''
        if self.getcfg('parallel'):
            paracmd = "-j %s" % self.getcfg('parallel')

        self.updatecfg('makeopts', 'LIBDIR=""')

        if self.toolkit().opts['usempi']:
            if self.toolkit().opts['pic']:
                self.updatecfg('makeopts', 'CC="$MPICC -fPIC"')
            else:
                self.updatecfg('makeopts', 'CC="$MPICC"')

        cmd = "%s make %s %s" % (self.getcfg('premakeopts'), paracmd, self.getcfg('makeopts'))

        # run make in build dir as well for recent version
        if LooseVersion(self.version()) >= LooseVersion("4"):
            try:
                os.chdir(self.parmetis_builddir)
                run_cmd(cmd, log_all=True, simple=True, log_output=verbose)
                os.chdir(self.getcfg('startfrom'))
            except OSError, err:
                self.log.error("Running cmd '%s' in %s failed: %s" % (cmd, self.parmetis_builddir, err))
        else:
            run_cmd(cmd, log_all=True, simple=True, log_output=verbose)

    def make_install(self):
        """
        Install by copying files over to the right places.

        Also create symlinks where expected by other packages (Lib directory).
        """
        includedir = os.path.join(self.installdir, 'include')
        libdir = os.path.join(self.installdir, 'lib')

        if LooseVersion(self.version()) >= LooseVersion("4"):
            # includedir etc changed in v4, use a normal make install
            cmd = "make install %s" % self.getcfg('installopts')
            try:
                os.chdir(self.parmetis_builddir)
                run_cmd(cmd, log_all=True, simple=True)
                os.chdir(self.getcfg('startfrom'))
            except OSError, err:
                self.log.error("Running '%s' in %s failed: %s" % (cmd, self.parmetis_builddir, err))

            # libraries
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build' ,'libmetis' ,'libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

            # include files
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build', 'metis', 'include', 'metis.h')
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
                # some applications (SuiteSparse) can only use METIS (not ParMETIS), but header files are the same
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

        # other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and header files in the Lib directory (capital L). The following symlink are hence created.
        try:
            llibdir = os.path.join(self.installdir, 'Lib')
            os.symlink(libdir, llibdir)
            for f in ['metis.h', 'parmetis.h']:
                os.symlink(os.path.join(includedir, f), os.path.join(libdir, f))
        except OSError, err:
            self.log.error("Something went wrong during symlink creation: %s" % err)

    def sanitycheck(self):
        """Custom sanity check for ParMETIS."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files': ['include/%smetis.h' % x for x in ["", "par"]] +
                                                      ['lib/lib%smetis.a' % x for x in ["", "par"]],
                                             'dirs':['Lib']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
