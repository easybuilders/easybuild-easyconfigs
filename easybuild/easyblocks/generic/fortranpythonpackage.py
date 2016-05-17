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
EasyBuild support for building and installing Python packages using Fortran, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class FortranPythonPackage(PythonPackage):
    """Extends PythonPackage to add a Fortran compiler to the make call"""

    def build_step(self):
        """Customize the build step by adding compiler-specific flags to the build command."""

        comp_fam = self.toolchain.comp_family()

        if comp_fam == toolchain.INTELCOMP:  # @UndefinedVariable
            cmd = "%s setup.py build --compiler=intel --fcompiler=intelem" % self.python_cmd

        elif comp_fam in [toolchain.GCC, toolchain.CLANGGCC]:  # @UndefinedVariable
            cmdprefix = ""
            ldflags = os.getenv('LDFLAGS')
            if ldflags:
                # LDFLAGS should not be set when building numpy/scipy, because it overwrites whatever numpy/scipy sets
                # see http://projects.scipy.org/numpy/ticket/182
                # don't unset it with os.environ.pop('LDFLAGS'), doesn't work in Python 2.4,
                # see http://bugs.python.org/issue1287
                cmdprefix = "unset LDFLAGS && "
                self.log.debug("LDFLAGS was %s, will be cleared before %s build with '%s'" % (self.name,
                                                                                              ldflags,
                                                                                              cmdprefix))

            cmd = "%s %s setup.py build --fcompiler=gnu95" % (cmdprefix, self.python_cmd)

        else:
            raise EasyBuildError("Unknown family of compilers being used: %s", comp_fam)

        run_cmd(cmd, log_all=True, simple=True)
