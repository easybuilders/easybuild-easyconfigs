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
EasyBuild support for Python packages that are configured with 'python configure/make/make install', implemented as an easyblock

@author: Bart Verleye (Centre for eResearch, Auckland)
@author: Kenneth Hoste (Ghent University)
"""
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.run import run_cmd
from easybuild.easyblocks.python import EXTS_FILTER_PYTHON_PACKAGES


class ConfigureMakePythonPackage(ConfigureMake, PythonPackage):
    """
    Build a Python package and module with 'python configure/make/make install'.

    Implemented by using:
    - a custom implementation of configure_step
    - using the build_step and install_step from ConfigureMake
    - using the sanity_check_step and make_module_extra from PythonPackage
    """
    @staticmethod
    def extra_options():
        """Extra easyconfig parameters for Python packages being installed with python configure/make/make install."""
        extra = PythonPackage.extra_options()
        return ConfigureMake.extra_options(extra_vars=extra)

    def __init__(self, *args, **kwargs):
        """Initialize with PythonPackage."""
        PythonPackage.__init__(self, *args, **kwargs)

    def configure_step(self):
        """Configure build using 'python configure'."""
        cmd = "%s python %s" % (self.cfg['preconfigopts'], self.cfg['configopts'])
        run_cmd(cmd, log_all=True)

    def build_step(self, *args, **kwargs):
        """Build Python package with 'make'."""
        return ConfigureMake.build_step(self, *args, **kwargs)

    def test_step(self, *args, **kwargs):
        """Test Python package."""
        PythonPackage.test_step(self, *args, **kwargs)

    def install_step(self, *args, **kargs):
        """Install with 'make install'."""
        return ConfigureMake.install_step(self, *args, **kargs)

    def sanity_check_step(self, *args, **kwargs):
        """
        Custom sanity check for Python packages
        """
        return PythonPackage.sanity_check_step(self, EXTS_FILTER_PYTHON_PACKAGES, *args, **kwargs)

    def make_module_extra(self):
        """Add extra Python package module parameters"""
        return PythonPackage.make_module_extra(self)
