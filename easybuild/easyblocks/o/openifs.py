##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing OpenIFS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_OpenIFS(EasyBlock):
    """Support for building/installing OpenIFS."""

    def configure_step(self):
        """Custom configuration procedure for OpenIFS."""
        # make sure use of MPI is enabled
        if not self.toolchain.options.get('usempi', None):
            raise EasyBuildError("Use of MPI should be enabled, set 'usempi' toolchain option to 'True'.")

        # configure build via OIFS_* environment variables
        env.setvar('OIFS_ARCH', 'x86_64')
        env.setvar('OIFS_BUILD', 'opt')
        if self.toolchain.comp_family() == toolchain.GCC:
            env.setvar('OIFS_COMP', 'gnu')
        elif self.toolchain.comp_family() == toolchain.INTELCOMP: 
            env.setvar('OIFS_COMP', 'intel')
        else:
            raise EasyBuildError("Unknown compiler used, don't know how to set $OIFS_COMP.")

        # give EasyBuild control over compiler options
        env.setvar('OIFS_CC', os.getenv('CC'))
        env.setvar('OIFS_CFLAGS', os.getenv('CFLAGS'))
        env.setvar('OIFS_FC', os.getenv('F90'))
        env.setvar('OIFS_FFLAGS', os.getenv('F90FLAGS'))

        # set location of dependencies
        grib_api_root = get_software_root('grib_api')
        if grib_api_root:
            env.setvar('OIFS_GRIB_API_DIR', grib_api_root)
        else:
            raise EasyBuildError("grib_api module not loaded")

        env.setvar('OIFS_LAPACK_LIB', "-L%s %s" % (os.getenv('LAPACK_LIB_DIR'), os.getenv('LIBLAPACK')))

    def build_step(self):
        """Custom build procedure for OpenIFS."""
        try:
            os.chdir('make')
        except OSError, err:
            raise EasyBuildError("Failed to move to 'make' dir: %s", err)

        # enable parallel build
        par = self.cfg['parallel']
        cmd = "fcm make -v -j %s -f fcmcfg/oifs.cfg" % par
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for OpenIFS: copy bin and include files."""
        try:
            srcdir = os.path.join(self.cfg['start_dir'], 'make', os.getenv('OIFS_BUILD'), 'oifs')
            bindir = os.path.join(self.installdir, 'bin')
            os.makedirs(bindir)
            shutil.copy2(os.path.join(srcdir, 'bin', 'master.exe'), bindir)
            shutil.copytree(os.path.join(srcdir, 'include'), os.path.join(self.installdir, 'include'))
        except OSError, err:
            raise EasyBuildError("Failed to install OpenIFS: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for OpenIFS."""
        custom_paths = {
            'files': ['bin/master.exe'],
            'dirs': ['include'],
        }

        super(EB_OpenIFS, self).sanity_check_step(custom_paths=custom_paths)

