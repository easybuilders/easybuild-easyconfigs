##
# Copyright 2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd_qa


class EB_Qt(ConfigureMake):
    """
    Support for building and installing Qt.
    """

    def configure_step(self):
        """Configure Qt using interactive `configure` script."""

        self.cfg.update('configopts', '-release')

        comp_fam = self.toolchain.comp_family()
        if comp_fam in [toolchain.GCC]:  #@UndefinedVariable
            self.cfg.update('configopts', '-platform linux-g++-64')
        elif comp_fam in [toolchain.INTELCOMP]:  #@UndefinedVariable
            self.cfg.update('configopts', '-platform linux-icc-64')
        else:
            self.log.error("Don't know which platform to set based on compiler family.")

        cmd = "%s ./configure --prefix=%s %s" % (self.cfg['preconfigopts'], self.installdir, self.cfg['configopts'])
        qa = {
            "Type 'o' if you want to use the Open Source Edition.": 'o',
            "Do you accept the terms of either license?": 'yes',
        }
        no_qa = [
            "for .*pro",
            r"%s.*" % os.getenv('CXX').replace('+', '\\+'),  # need to escape + in 'g++'
            "Reading .*",
            "WARNING .*",
            "Project MESSAGE:.*",
            "rm -f .*",
        ]
        run_cmd_qa(cmd, qa, no_qa=no_qa, log_all=True, simple=True)

    def build_step(self):
        """Set $LD_LIBRARY_PATH before calling make, to ensure that all required libraries are found during linking."""
        # cfr. https://elist.ornl.gov/pipermail/visit-developers/2011-September/010063.html
        self.cfg.update('premakeopts', 'LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH' % os.path.join(self.cfg['start_dir'], 'lib'))

        super(EB_Qt, self).build_step()

    def sanity_check_step(self):
        """Custom sanity check for Qt."""

        custom_paths = {
            'files': ["lib/libQtCore.so"],
            'dirs': ["bin", "include", "plugins"],
        }

        super(EB_Qt, self).sanity_check_step(custom_paths=custom_paths)
