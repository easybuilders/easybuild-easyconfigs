##
# Copyright 2016-2016 Ghent University
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
EasyBuild support for building and installing pplacer, implemented as an easyblock

@author: Kenneth Hoste (HPC-UGent)
"""
import os
import shutil

import easybuild.tools.environment as env
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import write_file
from easybuild.tools.run import run_cmd

from easybuild.easyblocks.generic.configuremake import ConfigureMake


# see http://matsen.github.io/pplacer/compiling.html#opam
class EB_pplacer(ConfigureMake):
    """Support for building/installing pplacer."""

    def configure_step(self):
        """Custom configuration procedure for pplacer."""
        # install dir has to be non-existing when we start (it may be there from a previous (failed) install
        try:
            if os.path.exists(self.installdir):
                shutil.rmtree(self.installdir)
            self.log.warning("Existing install directory %s removed", self.installdir)

        except OSError as err:
            raise EasyBuildError("Failed to remove %s: %s", self.installdir, err)

        # configure OPAM to install pplacer dependencies
        env.setvar('OPAMROOT', self.installdir)
        run_cmd("opam init")

        run_cmd("opam repo add pplacer-deps %s/pplacer-opam-repository*/" % self.builddir)
        run_cmd("opam update pplacer-deps")

        env.setvar('OCAML_BACKEND', 'gcc')

        run_cmd("eval `opam config env` && cat opam-requirements.txt | xargs -t opam install -y")

        txt = "let version = \"v%s\"\n" % self.version
        write_file(os.path.join(self.builddir, 'pplacer-%s' % self.version, 'common_src', 'version.ml'), txt)

    def build_step(self):
        """Custom build procedure for pplacer: set up OPAM environment and run 'make'."""
        self.cfg.update('prebuildopts', "eval `opam config env` && ")
        super(EB_pplacer, self).build_step()

    def install_step(self):
        """Custom install procedure for pplacer: copy 'bin' directory to install directory."""
        from_bindir = os.path.join(self.builddir, 'pplacer-%s' % self.version, 'bin')
        to_bindir = os.path.join(self.installdir, 'bin')
        try:
            shutil.copytree(from_bindir, to_bindir)
        except OSError as err:
            raise EasyBuildError("Failed to copy %s to %s: %s", from_bindir, to_bindir, err)

    def sanity_check_step(self):
        """Custom sanity check for pplacer."""
        custom_paths = {
            'files': ['bin/guppy', 'bin/pplacer', 'bin/rppr'],
            'dirs': [],
        }
        custom_commands = [('pplacer', "--version | grep %s" % self.version)]

        super(EB_pplacer, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)
