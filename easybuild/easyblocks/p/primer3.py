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
EasyBuild support for Primer3, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_Primer3(ConfigureMake):
    """
    Support for building Primer3.
    Configure and build in installation dir.
    """

    def __init__(self, *args, **kwargs):
        """Custom initialization for Primer3: build in install dir, set correct bin dir, specify to start from 'src'."""
        super(EB_Primer3, self).__init__(*args, **kwargs)
        self.build_in_installdir = True
        self.bindir = "%s-%s/src" % (self.name.lower(), self.version)

    def guess_start_dir(self):
        """Set correct start directory."""
        super(EB_Primer3, self).guess_start_dir()
        if os.path.exists('src'):
            try:
                os.chdir('src')
            except OSError, err:
                raise EasyBuildError("Failed to move to 'src' subdirectory: %s", err)

    def configure_step(self):
        """Configure Primer3 build by setting make options."""
        self.cfg.update('buildopts', 'CC="%s" CPP="%s" O_OPTS="%s" all' % (os.getenv('CC'),
                                                                         os.getenv('CXX'),
                                                                         os.getenv('CFLAGS')))

    # default build_step should be fine

    def install_step(self):
        """(no make install)"""
        pass

    def sanity_check_step(self):
        """Custom sanity check for Primer3."""

        custom_paths = {
                        'files':["%s/%s" % (self.bindir, x) for x in ["primer3_core", "ntdpal",
                                                                      "oligotm", "long_seq_tm_test"]],
                        'dirs':[]
                       }

        super(EB_Primer3, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Correct suggestion for PATH variable."""

        guesses = super(EB_Primer3, self).make_module_req_guess()

        guesses.update({'PATH': [self.bindir]})

        return guesses
