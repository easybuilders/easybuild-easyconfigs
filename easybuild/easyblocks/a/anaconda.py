##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for building and installing Anaconda, implemented as an easyblock

@author: Jillian Rowe (New York University Abu Dhabi)
@author: Kenneth Hoste (HPC-UGent)
"""

import os
import stat

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, rmtree2
from easybuild.tools.run import run_cmd


class EB_Anaconda(Binary):
    """Support for building/installing Anaconda."""

    def install_step(self):
        """Copy all files in build directory to the install directory"""

        rmtree2(self.installdir)
        install_script = self.src[0]['name']

        adjust_permissions(os.path.join(self.builddir, install_script), stat.S_IRUSR|stat.S_IXUSR)
        
        cmd = "%s ./%s -p %s -b -f" % (self.cfg['preinstallopts'], install_script, self.installdir)
        self.log.info("Installing %s using command '%s'..." % (self.name, cmd))
        run_cmd(cmd, log_all=True, simple=True)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        return {
            'MANPATH': ['man', os.path.join('share', 'man')],
            'PATH': ['bin', 'sbin'],
            'PKG_CONFIG_PATH': [os.path.join(x, 'pkgconfig') for x in ['lib', 'lib32', 'lib64', 'share']],
        }

    def sanity_check_step(self):
        """
        Custom sanity check for Anaconda
        """
        custom_paths = {
            'files': [os.path.join('bin', x) for x in ['2to3', 'conda', 'ipython', 'pydoc', 'python', 'sqlite3']],
            'dirs': ['bin', 'etc', 'lib', 'pkgs'],
        }
        super(EB_Anaconda, self).sanity_check_step(custom_paths=custom_paths)
