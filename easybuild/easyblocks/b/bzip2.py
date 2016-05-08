##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for bzip2, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import glob
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_bzip2(ConfigureMake):
    """Support for building and installing bzip2."""

    # no configure script
    def configure_step(self):
        """Set extra configure options (CC, CFLAGS)."""

        self.cfg.update('prebuildopts', "make -f Makefile-libbz2_so && ")
        self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CC'))
        self.cfg.update('buildopts', "CFLAGS='-Wall -Winline %s -g $(BIGFILES)'" % os.getenv('CFLAGS'))
    
    def install_step(self):
        """Install in non-standard path by passing PREFIX variable to make install."""

        self.cfg.update('installopts', "PREFIX=%s" % self.installdir)
        
        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'lib/')
        os.mkdir(destdir)
        dynamic_libs_to_copy = glob.glob('libbz2.so.*')

        # copy dynamic libraries to install_dir/lib
        try:
            for lib in dynamic_libs_to_copy:
                os.system('mv %s %s' % (lib, destdir)) # no easy way to copy sysmlinks using python shutil?
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", lib, destdir, err)

        # create symlink libbz2.so >> libbz2.so.1.0.6
        os.chdir(destdir)
        libname = 'libbz2.so.%s' % self.cfg['version']
        os.symlink('libbz2.so.%s' % self.cfg['version'], 'libbz2.so') 
        os.chdir(srcdir)
        
        super(EB_bzip2, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for bzip2."""

        custom_paths = {
                        'files': ["bin/%s" % x for x in ["bunzip2", "bzcat", "bzdiff", "bzgrep",
                                                         "bzip2", "bzip2recover", "bzmore"]] +
                                 ['lib/libbz2.a', 'lib/libbz2.so.%s' % self.cfg['version'], 'lib/libbz2.so', 'include/bzlib.h'],
                         'dirs': []
                        }

        super(EB_bzip2, self).sanity_check_step(custom_paths=custom_paths)
