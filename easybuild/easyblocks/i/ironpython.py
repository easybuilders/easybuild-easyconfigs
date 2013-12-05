##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for IronPython, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd


class EB_IronPython(EasyBlock):
    """Support for building/installing IronPython."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for IronPython easyblock, indicate building in installdir."""
        super(EB_IronPython, self).__init__(*args, **kwargs)
        
        self.subdir = None
        
        self.build_in_installdir = True

    def configure_step(self):
        """No dedicated configure step for IronPython."""
        pass
    
    def build_step(self):
        """No dedicated build step for IronPython."""
        pass

    def install_step(self):        
        """Custom install step for IronPython, using xbuild command."""

        cmd = "xbuild /p:Configuration=Release Solutions/%s.sln" % self.name
        run_cmd(cmd, log_all=True, simple=True)

        try:
            self.subdir = os.listdir(self.installdir)[0]
        except OSError, err:
            self.log.error("Failed to determine IronPython install subdir: %s" % err)

    def sanity_check_step(self):
        """Custom sanity check for IronPython."""

        binpath = os.path.join(self.subdir, "bin", "Release")
        custom_paths = {
            'files': [os.path.join(binpath, x) for x in ['ipy.exe', 'ipy64.exe', 'ipyw.exe', 'ipyw64.exe']],
            'dirs': [os.path.join(self.subdir, x) for x in ['Config', 'Runtime', 'Tools', 'Util']],
        }
        super(EB_IronPython, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Add IronPython binaries path to $PATH."""

        guesses = super(EB_IronPython, self).make_module_req_guess()
        guesses.update({
            'PATH': [os.path.join(self.subdir, "bin", "Release")],
        })
        return guesses
