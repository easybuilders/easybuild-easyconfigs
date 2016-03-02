##
# Copyright 2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for building and installing IMOD, implemented as an easyblock

@author: Benjamin Roberts (Landcare Research NZ Ltd)
"""
import os
import shutil

from easybuild.easyblocks.generic.binary import Binary
from easybuild.tools.filetools import rmtree2

class EB_IMOD(Binary):
    """Support for building/installing IMOD."""

    def install_step(self):
        """Install IMOD using install script."""

        # -dir: Choose location of installation directory
        # -skip: do not attempt to deploy resource files in /etc
        # -yes: do not prompt for confirmation
        cmd = "tcsh {0}_{1}{2}.csh -dir {3} -skip -yes".format(self.name.lower(), self.version, self.cfg['versionsuffix'], self.installdir)
        run_cmd(cmd, log_all=True, simple=True)
        
        # The assumption by the install script is that installdir will be something
        # like /usr/local. So it creates, within the specified install location, a
        # number of additional directories within which to install IMOD. We will,
        # therefore, move the contents of these directories up and throw away the
        # directories themselves. Doing so apparently is not a problem so long as
        # IMOD_DIR is correctly set in the module.
        dir1 = os.path.join(self.installdir, self.name)
        dir2 = os.path.join(self.installdir, "{0}_{1}".format(self.name.lower(), self.version))
        for file in os.listdir(dir1):
            shutil.move(os.path.join(dir1, file), self.installdir)
        rmtree2(dir1)
        rmtree2(dir2)

    def sanity_check_step(self):
        """Custom sanity check for IMOD."""
        custom_paths = {
            'files': ['IMOD-linux.sh', 'IMOD-linux.csh', 'installIMOD'],
            'dirs': ['bin', 'lib'],
        }
        super(EB_IMOD, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define IMOD specific variables in generated module file."""
        txt = super(EB_IMOD, self).make_module_extra()
        txt += self.module_generator.set_environment('IMOD_DIR', self.installdir)
        txt += self.module_generator.set_environment('IMOD_PLUGIN_DIR', os.path.join(self.installdir, 'lib', 'imodplug'))
        txt += self.module_generator.set_environment('IMOD_QTLIBDIR', os.path.join(self.installdir, 'qtlib'))
        if os.getenv('EBROOTJAVA') is not None:
            txt += self.module_generator.set_environment('IMOD_JAVADIR', os.getenv('EBROOTJAVA'))
        txt += self.module_generator.set_environment('FOR_DISABLE_STACK_TRACE', '1')
        txt += self.module_generator.set_alias('subm', "submfg $* &")
        txt += self.module_generator.msg_on_load("Please set the environment variable IMOD_CALIB_DIR if appropriate.")
        return txt
