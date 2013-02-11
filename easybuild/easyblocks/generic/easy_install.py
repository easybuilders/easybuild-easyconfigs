# #
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
# #
"""
EasyBuild support for installing Python packages with easy_install, implemented as an easyblock

@author: Kenneth Hoste (UGent)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.filetools import mkdir, run_cmd


class Easy_install(PythonPackage):
    """Installs a Python package using easy_install."""

    def build_step(self):
        """No seperate build step when using easy_install."""
        pass

    def test_step(self):
        """No build step, so no pre-install testing."""
        pass

    def install_step(self):
        """Install Python package to a custom path using easy_install."""

        # create expected directories
        abs_pylibdir = os.path.join(self.installdir, self.pylibdir)
        mkdir(abs_pylibdir, parents=True)

        # set PYTHONPATH as expected
        pythonpath = os.getenv('PYTHONPATH')
        env.setvar('PYTHONPATH', ":".join([x for x in [abs_pylibdir, pythonpath] if x is not None]))

        # actually install Python package
        cmd = "easy_install --always-copy --prefix=%s %s ." % (self.installdir, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        # restore PYTHONPATH if it was set
        if pythonpath is not None:
            env.setvar('PYTHONPATH', pythonpath)

    def run(self):
        """Perform the actual Python package build/installation procedure"""

        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % (self.name,
                                                                                                            self.src))
        super(PythonPackage, self).run(unpack_src=True)

        self.install_step()

