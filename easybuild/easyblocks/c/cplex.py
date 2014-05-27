##
# Copyright 2009-2013 Ghent University
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
from easybuild.tools.filetools import run_cmd_qa


class EB_CPLEX(Binary):
    """
    Support for installing CPLEX.
    Version 12.2 has a self-extracting binary with a Java installer
    """

    def __init__(self, *args, **kwargs):
        """Initialize CPLEX-specific variables."""
        super(EB_CPLEX, self).__init__(*args, **kwargs)
        self.bindir = None

    @staticmethod
    def extra_options():
        extra_vars = [
            # staged install via a tmp dir can help with the hard (potentially faulty) check on available disk space
            ('staged_install', [False, "Should the installation should be staged via a temporary dir?", CUSTOM]),
        ]
        return Binary.extra_options(extra_vars)

    def install_step(self):
        """CPLEX has an interactive installer, so use Q&A"""

        tmpdir = os.path.join(self.builddir, 'tmp')
        stagedir = os.path.join(self.builddir, 'staged')
        try:
            os.chdir(self.builddir)
            os.makedirs(tmpdir)
            os.makedirs(stagedir)
        except OSError, err:
            self.log.exception("Failed to prepare for installation: %s" % err)

        env.setvar('IATEMPDIR', tmpdir)
        dst = os.path.join(self.builddir, self.src[0]['name'])

        cmd = "%s -i console" % dst

        install_target = self.installdir
        if self.cfg['staged_install']:
            install_target = stagedir

        qanda = {
            "PRESS <ENTER> TO CONTINUE:": '',
            'Press Enter to continue viewing the license agreement, or enter' \
            ' "1" to accept the agreement, "2" to decline it, "3" to print it,' \
            ' or "99" to go back to the previous screen.:': '1',
            'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :': install_target,
            'IS THIS CORRECT? (Y/N):': 'y',
            'PRESS <ENTER> TO INSTALL:': '',
            "PRESS <ENTER> TO EXIT THE INSTALLER:": '',
            "CHOOSE LOCALE BY NUMBER:": '',
            "Choose Instance Management Option:": '',
        }
        noqanda = [r'Installing\.\.\..*\n.*------.*\n\n.*============.*\n.*$']

        run_cmd_qa(cmd, qanda, no_qa=noqanda, log_all=True, simple=True)

        if self.cfg['staged_install']:
            # move staged installation to actual install dir
            try:
                # copytree expects target directory to not exist yet
                shutil.rmtree(self.installdir)
                shutil.copytree(stagedir, self.installdir)
            except OSError, err:
                self.log.error("Failed to move staged install from %s to %s: %s" % (stagedir, self.installdir, err))

        try:
            os.chmod(self.installdir, stat.S_IRWXU | stat.S_IXOTH | stat.S_IXGRP | stat.S_IROTH | stat.S_IRGRP)
        except OSError, err:
            self.log.exception("Can't set permissions on %s: %s" % (self.installdir, err))

        # determine bin dir
        os.chdir(self.installdir)
        binglob = 'cplex/bin/x86-64*'
        bins = glob.glob(binglob)

        if len(bins) == 1:
            self.bindir = bins[0]
        elif len(bins) > 1:
            self.log.error("More than one possible path for bin found: %s" % bins)
        else:
            self.log.error("No bins found using %s in %s" % (binglob, self.installdir))

    def make_module_extra(self):
        """Add installdir to path and set CPLEX_HOME"""

        txt = super(EB_CPLEX, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("PATH", [self.bindir])
        txt += self.moduleGenerator.set_environment("CPLEX_HOME", "$root/cplex")
        self.log.debug("make_module_extra added %s" % txt)
        return txt

    def sanity_check_step(self):
        """Custom sanity check for CPLEX"""

        custom_paths = {
            'files':["%s/%s" % (self.bindir, x) for x in ["convert", "cplex", "cplexamp"]],
            'dirs':[],
        }

        super(EB_CPLEX, self).sanity_check_step(custom_paths=custom_paths)
