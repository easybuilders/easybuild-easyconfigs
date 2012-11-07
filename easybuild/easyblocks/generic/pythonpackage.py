##
# Copyright 2009-2012 Ghent University
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for Python packages, implemented as an easyblock
"""
import os

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd, mkdir
from easybuild.tools.modules import get_software_version


class PythonPackage(EasyBlock):
    """Builds and installs a Python package, and provides a dedicated module file."""

    def __init__(self, *args, **kwargs):
        """Initialize custom variables."""
        super(PythonPackage, self).__init__(*args, **kwargs)

        # template for Python packages lib dir
        self.pylibdir = os.path.join("lib", "python%s", "site-packages")

    def configure_step(self):
        """Set Python packages lib dir."""

        self.log.debug("PythonPackage: configuring")

        python_version = get_software_version('Python')
        if not python_version:
            self.log.error('Python module not loaded.')

        python_short_ver = ".".join(python_version.split(".")[0:2])

        self.pylibdir = self.pylibdir % python_short_ver

        self.log.debug("pylibdir: %s" % self.pylibdir)

    def build_step(self):
        """Build Python package using setup.py"""

        cmd = "python setup.py build"
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install Python package to a custom path using setup.py"""

        abs_pylibdir = os.path.join(self.installdir, self.pylibdir)

        mkdir(abs_pylibdir, parents=True)

        pythonpath = os.getenv('PYTHONPATH')
        env.setvar('PYTHONPATH', "%s:%s" % (abs_pylibdir, pythonpath))

        cmd = "python setup.py install --prefix=%s %s" % (self.installdir, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        env.setvar('PYTHONPATH', pythonpath)

    def sanity_check_step(self, custom_paths=None, custom_commands=None):
        """
        Custom sanity check for Python packages
        """
        if not custom_paths:
            custom_paths = {
                            'files': [],
                            'dirs': ["%s/%s" % (self.pylibdir, self.name.lower())]
                           }

        super(PythonPackage, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_extra(self):
        """Add install path to PYTHONPATH"""

        txt = super(PythonPackage, self).make_module_extra()

        txt += "prepend-path\tPYTHONPATH\t%s\n" % os.path.join(self.installdir , self.pylibdir)

        return txt
