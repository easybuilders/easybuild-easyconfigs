##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for OCaml packages, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class OCamlPackage(ExtensionEasyBlock):
    """Builds and installs OCaml packages using OPAM package manager."""

    def configure_step(self):
        """Raise error when configure step is run: installing OCaml packages stand-alone is not supported (yet)"""
        raise EasyBuildError("Installing OCaml packages stand-alone is not supported (yet)")

    def run(self):
        """Perform OCaml package installation (as extension)."""
        # install using 'opam install'
        run_cmd("eval `opam config env` && opam install -yv %s.%s" % (self.name, self.version))

        # 'opam pin add' fixes the version of the package
        # see https://opam.ocaml.org/doc/Usage.html#opampin
        run_cmd("eval `opam config env` && opam pin -yv add %s %s" % (self.name, self.version))
