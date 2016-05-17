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
EasyBuild support for building and installing Qt, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd_qa
from easybuild.tools.systemtools import get_shared_lib_ext

class EB_Qt(ConfigureMake):
    """
    Support for building and installing Qt.
    """

    @staticmethod
    def extra_options():
        extra_vars = {
             'platform': [None, "Target platform to build for (e.g. linux-g++-64, linux-icc-64)", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """Configure Qt using interactive `configure` script."""

        self.cfg.update('configopts', '-release')

        platform = None
        comp_fam = self.toolchain.comp_family()
        if self.cfg['platform']:
            platform = self.cfg['platform']
        # if no platform is specified, try to derive it based on compiler in toolchain
        elif comp_fam in [toolchain.GCC]:  #@UndefinedVariable
            platform = 'linux-g++-64'
        elif comp_fam in [toolchain.INTELCOMP]:  #@UndefinedVariable
            platform = 'linux-icc-64'
                
        if platform:
            self.cfg.update('configopts', "-platform %s" % platform)
        else:
            raise EasyBuildError("Don't know which platform to set based on compiler family.")

        cmd = "%s ./configure --prefix=%s %s" % (self.cfg['preconfigopts'], self.installdir, self.cfg['configopts'])
        qa = {
            "Type 'o' if you want to use the Open Source Edition.": 'o',
            "Do you accept the terms of either license?": 'yes',
        }
        no_qa = [
            "for .*pro",
            r"%s.*" % os.getenv('CXX', '').replace('+', '\\+'),  # need to escape + in 'g++'
            "Reading .*",
            "WARNING .*",
            "Project MESSAGE:.*",
            "rm -f .*",
            'Creating qmake...',
        ]
        run_cmd_qa(cmd, qa, no_qa=no_qa, log_all=True, simple=True, maxhits=120)

    def build_step(self):
        """Set $LD_LIBRARY_PATH before calling make, to ensure that all required libraries are found during linking."""
        # cfr. https://elist.ornl.gov/pipermail/visit-developers/2011-September/010063.html

        if LooseVersion(self.version) >= LooseVersion('5.6'):
            libdirs = ['qtbase', 'qtdeclarative']
        else:
            libdirs = ['']

        libdirs = [os.path.join(self.cfg['start_dir'], d, 'lib') for d in libdirs]
        self.cfg.update('prebuildopts', 'LD_LIBRARY_PATH=%s' % os.pathsep.join(libdirs + ['$LD_LIBRARY_PATH']))

        super(EB_Qt, self).build_step()

    def sanity_check_step(self):
        """Custom sanity check for Qt."""

        libversion = ''
        if LooseVersion(self.version) >= LooseVersion('5'):
            libversion = self.version.split('.')[0]

        custom_paths = {
            'files': ["lib/libQt%sCore.%s" % (libversion, get_shared_lib_ext())],
            'dirs': ["bin", "include", "plugins"],
        }

        super(EB_Qt, self).sanity_check_step(custom_paths=custom_paths)
