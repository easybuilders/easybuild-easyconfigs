##
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
##
"""
EasyBuild support for installing VSC-tools Python packages, implemented as an easyblock

@author: Kenneth Hoste (UGent)
"""
import os

from easybuild.easyblocks.generic.versionindependendpythonpackage import VersionIndependendPythonPackage


# EasyBuild provides its own 'vsc' namespace, that shouldn't be mixed with a 'vsc' namespace available somewhere else
# therefore, we need a dedicated easyblock for VSC-tools packages like vsc-base, vsc-mympirun, etc.
class VSCPythonPackage(VersionIndependendPythonPackage):
    """Support for install VSC Python packages."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for VSC Python packages."""
        super(VSCPythonPackage, self).__init__(*args, **kwargs)
        self.log.deprecated("VSCPythonPackage is only there because EasyBuild provides a 'vsc' namespace too", '2.0')

    def sanity_check_step(self, *args, **kwargs):
        """Custom sanity check for VSC-tools packages."""
        pythonpath = os.environ.get('PYTHONPATH', '')
        os.environ['PYTHONPATH'] = ''
        kwargs.update({'exts_filter': ('python -s -S -c "import %(ext_name)s"', "")})
        super(VSCPythonPackage, self).sanity_check_step(*args, **kwargs)
        os.environ['PYTHONPATH'] = pythonpath
