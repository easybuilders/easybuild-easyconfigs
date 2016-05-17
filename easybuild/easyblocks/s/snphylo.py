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
EasyBuild support for SNPyhlo, implemented as an easyblock

@authors: Ewan Higgs (HPC-UGent)
@authors: Kenneth Hoste (HPC-UGent)
"""
import os
import re
import shutil
import stat

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, mkdir
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_SNPhylo(EasyBlock):
    """Support for building and installing SNPhylo."""

    def configure_step(self):
        """No configure step for SNPhylo."""
        pass

    def build_step(self):
        """No build step for SNPhylo."""

        # check for required dependencies
        for dep in ['MUSCLE', 'PHYLIP', 'Python', 'R']:
            if not get_software_root(dep):
                raise EasyBuildError("Required dependency '%s' not loaded", dep)

        # check for required R libraries
        rver = get_software_version('R')
        r_libs, _ = run_cmd("R --vanilla --no-save --slave -e 'print(installed.packages())'", simple=False)
        for rpkg in ['gdsfmt', 'getopt', 'SNPRelate', 'phangorn']:
            if not re.search(r'^%s\s.*%s' % (rpkg, rver), r_libs, re.M):
                raise EasyBuildError("Required R package '%s' not installed", rpkg)

        # run setup.sh, and send a bunch of newlines as stdin to 'answer' the Q&A;
        # all questions can be answered with the default answer (if the dependencies are specified correctly);
        # use run_cmd_qa doesn not work because of buffering issues (questions are not coming through)
        adjust_permissions('setup.sh', stat.S_IXUSR, add=True)
        (out, _) = run_cmd('bash ./setup.sh', inp='\n' * 10, simple=False)

        success_msg = "SNPHYLO is successfully installed!!!"
        if success_msg not in out:
            raise EasyBuildError("Success message '%s' not found in setup.sh output: %s", success_msg, out)

    def install_step(self):
        """Install by copying files/directories."""
        bindir = os.path.join(self.installdir, 'bin')
        binfiles = ['snphylo.sh', 'snphylo.cfg', 'snphylo.template']
        try:
            mkdir(bindir, parents=True)
            for binfile in binfiles:
                shutil.copy2(os.path.join(self.builddir, binfile), bindir)
            shutil.copytree(os.path.join(self.builddir, 'scripts'), os.path.join(self.installdir, 'scripts'))
        except OSError as err:
            raise EasyBuildError("Failed to copy SNPhylo files/dirs: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for SNPhylo."""
        custom_paths = {
            'files': ['bin/snphylo.sh', 'bin/snphylo.cfg', 'bin/snphylo.template'],
            'dirs': ['scripts'],
        }
        super(EB_SNPhylo, self).sanity_check_step(custom_paths=custom_paths)
