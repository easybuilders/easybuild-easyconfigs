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
EasyBuild support for CPLEX, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import glob
import os
import shutil
import stat

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd_qa


class EB_CPLEX(Binary):
    """
    Support for installing CPLEX.
    Version 12.2 has a self-extracting binary with a Java installer
    """

    def __init__(self, *args, **kwargs):
        """Initialize CPLEX-specific variables."""
        super(EB_CPLEX, self).__init__(*args, **kwargs)
        self.bindir = 'UNKNOWN'

    def install_step(self):
        """CPLEX has an interactive installer, so use Q&A"""

        tmpdir = os.path.join(self.builddir, 'tmp')
        stagedir = os.path.join(self.builddir, 'staged')
        try:
            os.chdir(self.builddir)
            os.makedirs(tmpdir)
            os.makedirs(stagedir)
        except OSError, err:
            raise EasyBuildError("Failed to prepare for installation: %s", err)

        env.setvar('IATEMPDIR', tmpdir)
        dst = os.path.join(self.builddir, self.src[0]['name'])

        cmd = "%s -i console" % dst

        qanda = {
            "PRESS <ENTER> TO CONTINUE:": '',
            'Press Enter to continue viewing the license agreement, or enter' \
            ' "1" to accept the agreement, "2" to decline it, "3" to print it,' \
            ' or "99" to go back to the previous screen.:': '1',
            'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :': self.installdir,
            'IS THIS CORRECT? (Y/N):': 'y',
            'PRESS <ENTER> TO INSTALL:': '',
            "PRESS <ENTER> TO EXIT THE INSTALLER:": '',
            "CHOOSE LOCALE BY NUMBER:": '',
            "Choose Instance Management Option:": '',
        }
        noqanda = [r'Installing\.\.\..*\n.*------.*\n\n.*============.*\n.*$']

        run_cmd_qa(cmd, qanda, no_qa=noqanda, log_all=True, simple=True)

        try:
            os.chmod(self.installdir, stat.S_IRWXU | stat.S_IXOTH | stat.S_IXGRP | stat.S_IROTH | stat.S_IRGRP)
        except OSError, err:
            raise EasyBuildError("Can't set permissions on %s: %s", self.installdir, err)

    def post_install_step(self):
        """Determine bin directory for this CPLEX installation."""
        # handle staged install via Binary parent class
        super(EB_CPLEX, self).post_install_step()

        # determine bin dir
        os.chdir(self.installdir)
        binglob = 'cplex/bin/x86-64*'
        bins = glob.glob(binglob)

        if len(bins) == 1:
            self.bindir = bins[0]
        elif len(bins) > 1:
            raise EasyBuildError("More than one possible path for bin found: %s", bins)
        else:
            raise EasyBuildError("No bins found using %s in %s", binglob, self.installdir)

    def make_module_extra(self):
        """Add bin dirs and lib dirs and set CPLEX_HOME and CPLEXDIR"""
        txt = super(EB_CPLEX, self).make_module_extra()

        try:
            cwd = os.getcwd()
            os.chdir(self.installdir)
            bins = glob.glob(os.path.join('*', 'bin', 'x86-64*'))
            libs = glob.glob(os.path.join('*', 'lib', 'x86-64*', '*pic'))
            os.chdir(cwd)
        except OSError as err:
            raise EasyBuildError("Failed to determine bin/lib subdirs: %s", err)

        txt += self.module_generator.prepend_paths('PATH', [path for path in bins])
        txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', [path for path in bins+libs])

        txt += self.module_generator.set_environment('CPLEX_HOME', os.path.join(self.installdir, 'cplex'))
        txt += self.module_generator.set_environment('CPLEXDIR', os.path.join(self.installdir, 'cplex'))

        self.log.debug("make_module_extra added %s" % txt)
        return txt

    def sanity_check_step(self):
        """Custom sanity check for CPLEX"""
        custom_paths = {
            'files':["%s/%s" % (self.bindir, x) for x in ["convert", "cplex", "cplexamp"]],
            'dirs':[],
        }
        super(EB_CPLEX, self).sanity_check_step(custom_paths=custom_paths)
