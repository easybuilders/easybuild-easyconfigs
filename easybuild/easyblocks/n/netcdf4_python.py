##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing netcdf4-python, implemented as an easyblock.

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.modules import get_software_root


class EB_netcdf4_minus_python(PythonPackage):
    """Support for building and installing netcdf4-python"""

    def __init__(self, *args, **kwargs):
        """Custom constructor for netcdf4-python."""
        super(EB_netcdf4_minus_python, self).__init__(*args, **kwargs)
        self.options['modulename'] = 'netCDF4'

    def configure_step(self):
        """
        Configure and
        Test if python module is loaded
        """
        hdf5 = get_software_root('HDF5')
        if hdf5:
            env.setvar('HDF5_DIR', hdf5)
            szip = get_software_root('Szip')
            if szip:
                env.setvar('SZIP_DIR', szip)

        netcdf = get_software_root('netCDF')
        if netcdf:
            env.setvar('NETCDF4_DIR', netcdf)

        super(EB_netcdf4_minus_python, self).configure_step()

    def test_step(self):
        """Run netcdf4-python tests."""
        self.testinstall = True
        cwd = os.getcwd()
        self.testcmd = "cd %s/test && %s run_all.py && cd %s" % (self.cfg['start_dir'], self.python_cmd, cwd)
        super(EB_netcdf4_minus_python, self).test_step()

    def sanity_check_step(self):
        """Custom sanity check for netcdf4-python"""
        custom_paths = {
            'files': ['bin/nc3tonc4', 'bin/nc4tonc3', 'bin/ncinfo'],
            'dirs': [self.pylibdir],
        }
        return super(EB_netcdf4_minus_python, self).sanity_check_step(custom_paths=custom_paths)
