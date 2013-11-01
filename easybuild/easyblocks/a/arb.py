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
EasyBuild support for ARB, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd


class EB_ARB(ConfigureMake):
    """Support for building and installing ARB."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ARB, specify building in install dir."""
        super(EB_ARB, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def configure_step(self):
        """Run make without arguments instead of configure for ARB."""
        run_cmd("make")

    def install_step(self):
        """No installation step, ARB was built in installdir"""
        pass

    def make_module_req_guess(self):
        """Specify correct LD_LIBRARY_PATH and CPATH for this installation."""
        guesses = super(EB_ARB, self).make_module_req_guess()
        guesses.update({
            'CPATH': [os.path.join(self.cfg['start_dir'], "include")],
            'PATH': [os.path.join(self.cfg['start_dir'], "bin")],
            'LD_LIBRARY_PATH': [os.path.join(self.cfg['start_dir'], "lib")],
        })
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for ARB."""
        custom_paths = {
            'files': [os.path.join(self.cfg['start_dir'], "bin/arb") ],
            'dirs': [os.path.join(self.cfg['start_dir'], x) for x in ["lib"]],
        }
        super(EB_ARB, self).sanity_check_step(custom_paths=custom_paths)
