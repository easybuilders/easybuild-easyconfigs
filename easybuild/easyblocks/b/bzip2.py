### Copyright 2012 Kenneth Hoste
# Copyright 2012 Jens Timmerman
#
# This file is part of EasyBuild
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
EasyBuild support for bzip2, implemented as an easyblock
"""
import os

from easybuild.framework.configuremake import EB_ConfigureMake  #@UnresolvedImport


class EB_bzip2(EB_ConfigureMake):
    """Support for building and installing bzip2."""

    # no configure script
    def configure_step(self):
        """Set extra configure options (CC, CFLAGS)."""

        self.updatecfg('makeopts', 'CC="%s"' % os.getenv('CC'))
        self.updatecfg('makeopts', "CFLAGS='-Wall -Winline %s -g $(BIGFILES)'" % os.getenv('CFLAGS'))

    def install_step(self):
        """Install in non-standard path by passing PREFIX variable to make install."""

        self.updatecfg('installopts', "PREFIX=%s" % self.installdir)

        super(self.__class__, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for bzip2."""

        custom_paths = {
                        'files': ["bin/%s" % x for x in ["bunzip2", "bzcat", "bzdiff", "bzgrep",
                                                         "bzip2", "bzip2recover", "bzmore"]] +
                                 ['lib/libbz2.a', 'include/bzlib.h'],
                         'dirs': []
                        }

        super(self.__class__, self).sanity_check_step(custom_paths=custom_paths)
