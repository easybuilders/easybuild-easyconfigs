##
# Copyright 2009-2017 Ghent University
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

from easybuild.easyblocks.generic.packedbinary import PackedBinary
from easybuild.tools.run import run_cmd


class EB_IronPython(PackedBinary):
    """Support for building/installing IronPython."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for IronPython easyblock, indicate building in installdir."""
        super(EB_IronPython, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def extract_step(self):
        """Extract sources; strip off parent directory during unpack"""
        self.cfg.update('unpack_options', "--strip-components=1")
        super(EB_IronPython, self).extract_step()

    def install_step(self):
        """Custom install step for IronPython, using xbuild command."""

        cmd = "xbuild /p:Configuration=Release Solutions/%s.sln" % self.name
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for IronPython."""

        binpath = os.path.join('bin', 'Release')
        custom_paths = {
            'files': [os.path.join(binpath, x) for x in ['ipy.exe', 'ipy64.exe', 'ipyw.exe', 'ipyw64.exe']],
            'dirs': ['Config', 'Runtime', 'Tools', 'Util'],
        }
        super(EB_IronPython, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Add IronPython binaries path to $PATH."""
        guesses = super(EB_IronPython, self).make_module_req_guess()
        guesses.update({
            'PATH': [os.path.join('bin', 'Release')],
        })
        return guesses
