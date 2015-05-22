##
# Copyright 2015-2015 Ghent University
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
EasyBuild support for OCaml packages, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.ocaml import EXTS_FILTER_OCAML_PACKAGES
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.tools.run import run_cmd


class OCamlPackage(ExtensionEasyBlock):
    """Builds and installs OCaml packages using OPAM package manager."""

    def configure_step(self):
        """No separate configuration for OCaml packages."""
        env.setvar('OPAMROOT', self.installdir)

    def build_step(self):
        """No separate build procedure for OCaml packages."""
        pass

    def test_step(self):
        """No separate (standard) test procedure for OCaml packages."""
        pass

    def install_step(self):
        """Installing OCaml packages is just a glorified 'make install'."""
        # 'opam pin add' fixes the version of the package, and installs it if it's not there already (opam 1.2.x)
        # see https://opam.ocaml.org/doc/Usage.html#opampin
        run_cmd("opam pin -yv add %s %s" % (self.name, self.version))

    def run(self):
        """Perform OCaml package installation (as extension)."""
        env.setvar('OPAMROOT', os.path.join(self.installdir, 'opam'))
        self.install_step()

    def sanity_check_step(self, *args, **kwargs):
        """Custom sanity check for OCaml packages"""
        if not 'exts_filter' in kwargs:
            kwargs.update({'exts_filter': EXTS_FILTER_OCAML_PACKAGES})
        return super(OCamlPackage, self).sanity_check_step(*args, **kwargs)
