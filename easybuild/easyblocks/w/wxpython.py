##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for wxPython, implemented as an easyblock

@author: Balazs Hajgato (Vrije Universiteit Brussel)
"""

import os

from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd

class EB_wxPython(PythonPackage):
    """Support for installing the wxPython Python package."""

    def build_step(self):
        """Perform the actual Python package build procedure"""

        #wxPython configure, build, and install with one script
        cmd = 'python '
        cmd += os.path.join('wxPython', 'build-wxpython.py')
        cmd += ' --prefix={0} --wxpy_installdir={0} --install '.format(self.installdir)
        run_cmd(cmd, log_all=True, simple=True)
    
    def install_step(self):
        """Install performed during the build_step"""

        pass

    def make_installdir(self):
        """Installdir is already maked, do not delete it"""

        pass

    def sanity_check_step(self, *args, **kwargs):
        """The PythonPackage name is wx."""

        kwargs.update({'exts_filter': ('python -c "import wx"', "")})
        return super(PythonPackage, self).sanity_check_step(*args, **kwargs)
        
