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
EasyBuild support for Perl, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd

# perldoc -lm seems to be the safest way to test if a module is available, based on exitcode
EXTS_FILTER_PERL_PACKAGES = ("perldoc -lm %(ext_name)s ", "")


class EB_Perl(ConfigureMake):
    """Support for building and installing ParMETIS."""

    def configure_step(self):
        """Configure Perl build.
        run ./Configure instead of ./configure with some different options
        """
        configopts = " ".join([self.cfg['configopts'], "-Dusethreads", '-Dcc="$CC $CFLAGS"', '-Dinc_version_list=none',
                               '-Dccflags="$CFLAGS"',
                               ])
        cmd = './Configure -de %s -Dprefix="%s" ' % (configopts, self.installdir)
        run_cmd(cmd, log_all=True, simple=True)

    def prepare_for_extensions(self):
        """
        Set default class and filter for Perl packages
        """
        # build and install additional packages with PerlPackage easyblock
        self.cfg['exts_defaultclass'] = "PerlPackage"
        self.cfg['exts_filter'] = EXTS_FILTER_PERL_PACKAGES
