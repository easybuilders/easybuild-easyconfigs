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
EasyBuild support for building and installing EggLib, implemented as an easyblock

@author: Kenneth Hoste (HPC-UGent)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.build_log import EasyBuildError


class EB_EggLib(PythonPackage, ConfigureMake):
    """Support for building/installing EggLib."""

    def configure_step(self):
        """Configure EggLib build/install procedure."""
        # only need to configure Python library here, configuration of C++ library is done in install step
        PythonPackage.configure_step(self)

    def build_step(self):
        """No custom build procedure for EggLib; build/install is done in install_step."""
        pass

    def install_step(self):
        """Custom install procedure for EggLib: first build/install C++ library, then build Python library."""

        # build/install C++ library
        cpp_subdir = os.path.join(self.builddir, 'egglib-cpp-%s' % self.version)
        try:
            os.chdir(cpp_subdir)
        except OSError, err:
            raise EasyBuildError("Failed to move to: %s", err)

        ConfigureMake.configure_step(self)
        ConfigureMake.build_step(self)
        ConfigureMake.install_step(self)

        # header files and libraries must be found when building Python library
        for varname, subdir in [('CPATH', 'include'), ('LIBRARY_PATH', 'lib')]:
            env.setvar(varname, '%s:%s' % (os.path.join(self.installdir, subdir), os.environ.get(varname, '')))

        # build/install Python package
        py_subdir = os.path.join(self.builddir, 'egglib-py-%s' % self.version)
        try:
            os.chdir(py_subdir)
        except OSError, err:
            raise EasyBuildError("Failed to move to: %s", err)

        PythonPackage.build_step(self)

        self.cfg.update('installopts', "--install-lib %s" % os.path.join(self.installdir, self.pylibdir))
        self.cfg.update('installopts', "--install-scripts %s" % os.path.join(self.installdir, 'bin'))

        PythonPackage.install_step(self)

    def sanity_check_step(self):
        """Custom sanity check for EggLib."""
        custom_paths = {
            'files': ['bin/egglib', 'lib/libegglib-cpp.a'],
            'dirs': ['include/egglib-cpp', self.pylibdir],
        }
        super(EB_EggLib, self).sanity_check_step(custom_paths=custom_paths)
