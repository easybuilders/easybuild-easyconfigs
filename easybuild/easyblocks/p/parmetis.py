##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
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

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import shutil
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir
from easybuild.tools.run import run_cmd


class EB_ParMETIS(EasyBlock):
    """Support for building and installing ParMETIS."""

    def configure_step(self):
        """Configure ParMETIS build.
        For versions of ParMETIS < 4 , METIS is a seperate build
        New versions of ParMETIS include METIS
        
        Run 'cmake' in the build dir to get rid of a 'user friendly' 
        help message that is displayed without this step.
        """
        if LooseVersion(self.version) >= LooseVersion("4"):
            # tested with 4.0.2, now actually requires cmake to be run first
            # for both parmetis and metis

            self.cfg.update('configopts', '-DMETIS_PATH=../metis -DGKLIB_PATH=../metis/GKlib')

            self.cfg.update('configopts', '-DOPENMP="%s"' % self.toolchain.get_flag('openmp'))

            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', '-DCMAKE_C_COMPILER="$MPICC"')

            if self.toolchain.options['pic']:
                self.cfg.update('configopts', '-DCMAKE_C_FLAGS="-fPIC"')

            self.parmetis_builddir = 'build'
            try:
                os.chdir(self.parmetis_builddir)
                cmd = 'cmake .. %s -DCMAKE_INSTALL_PREFIX="%s"' % (self.cfg['configopts'],
                                                                   self.installdir)
                run_cmd(cmd, log_all=True, simple=True)
                os.chdir(self.cfg['start_dir'])
            except OSError, err:
                raise EasyBuildError("Running cmake in %s failed: %s", self.parmetis_builddir, err)

    def build_step(self, verbose=False):
        """Build ParMETIS (and METIS) using build_step."""

        paracmd = ''
        if self.cfg['parallel']:
            paracmd = "-j %s" % self.cfg['parallel']

        self.cfg.update('buildopts', 'LIBDIR=""')

        if self.toolchain.options['usempi']:
            if self.toolchain.options['pic']:
                self.cfg.update('buildopts', 'CC="$MPICC -fPIC"')
            else:
                self.cfg.update('buildopts', 'CC="$MPICC"')

        cmd = "%s make %s %s" % (self.cfg['prebuildopts'], paracmd, self.cfg['buildopts'])

        # run make in build dir as well for recent version
        if LooseVersion(self.version) >= LooseVersion("4"):
            try:
                os.chdir(self.parmetis_builddir)
                run_cmd(cmd, log_all=True, simple=True, log_output=verbose)
                os.chdir(self.cfg['start_dir'])
            except OSError, err:
                raise EasyBuildError("Running cmd '%s' in %s failed: %s", cmd, self.parmetis_builddir, err)
        else:
            run_cmd(cmd, log_all=True, simple=True, log_output=verbose)

    def install_step(self):
        """
        Install by copying files over to the right places.

        Also create symlinks where expected by other software (Lib directory).
        """
        includedir = os.path.join(self.installdir, 'include')
        libdir = os.path.join(self.installdir, 'lib')

        if LooseVersion(self.version) >= LooseVersion("4"):
            # includedir etc changed in v4, use a normal make install
            cmd = "make install %s" % self.cfg['installopts']
            try:
                os.chdir(self.parmetis_builddir)
                run_cmd(cmd, log_all=True, simple=True)
                os.chdir(self.cfg['start_dir'])
            except OSError, err:
                raise EasyBuildError("Running '%s' in %s failed: %s", cmd, self.parmetis_builddir, err)

            # libraries
            try:
                src = os.path.join(self.cfg['start_dir'], 'build' ,'libmetis' ,'libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying files to installation dir failed: %s", err)

            # include files
            try:
                src = os.path.join(self.cfg['start_dir'], 'build', 'metis', 'include', 'metis.h')
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying files to installation dir failed: %s", err)

        else:
            mkdir(libdir)
            mkdir(includedir)

            # libraries
            try:
                for fil in ['libmetis.a', 'libparmetis.a']:
                    src = os.path.join(self.cfg['start_dir'], fil)
                    dst = os.path.join(libdir, fil)
                    shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying files to installation dir failed: %s", err)

            # include files
            try:
                src = os.path.join(self.cfg['start_dir'], 'parmetis.h')
                dst = os.path.join(includedir, 'parmetis.h')
                shutil.copy2(src, dst)
                # some applications (SuiteSparse) can only use METIS (not ParMETIS), but header files are the same
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying files to installation dir failed: %s", err)

        # other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and header files in the Lib directory (capital L). The following symlink are hence created.
        try:
            llibdir = os.path.join(self.installdir, 'Lib')
            os.symlink(libdir, llibdir)
            for f in ['metis.h', 'parmetis.h']:
                os.symlink(os.path.join(includedir, f), os.path.join(libdir, f))
        except OSError, err:
            raise EasyBuildError("Something went wrong during symlink creation: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for ParMETIS."""

        custom_paths = {
                        'files': ['include/%smetis.h' % x for x in ["", "par"]] +
                                 ['lib/lib%smetis.a' % x for x in ["", "par"]],
                        'dirs':['Lib']
                       }

        super(EB_ParMETIS, self).sanity_check_step(custom_paths=custom_paths)
