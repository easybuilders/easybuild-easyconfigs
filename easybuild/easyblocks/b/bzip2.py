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
EasyBuild support for bzip2, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Pablo Escobar (sciCORE, UniBas)
"""
import glob
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_bzip2(ConfigureMake):
    """Support for building and installing bzip2."""

    @staticmethod
    def extra_options():
        """Add extra config options specific to bzip2."""
        extra_vars = {
            'with_shared_libs': [True, "Also build shared libraries", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars=extra_vars)

    # no configure script
    def configure_step(self):
        """Set extra options for 'make' command (CC, CFLAGS)."""

        if 'CC=' not in self.cfg['buildopts']:
            self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CC'))
        if 'CFLAGS=' not in self.cfg['buildopts']:
            self.cfg.update('buildopts', "CFLAGS='-Wall -Winline %s -g $(BIGFILES)'" % os.getenv('CFLAGS'))

    def install_step(self):
        """Install in non-standard path by passing PREFIX variable to make install."""

        self.cfg.update('installopts', "PREFIX=%s" % self.installdir)
        super(EB_bzip2, self).install_step()

        # also build & install shared libraries, if desired
        if self.cfg['with_shared_libs']:

            cmd = "%s make -f Makefile-libbz2_so %s" % (self.cfg['prebuildopts'], self.cfg['buildopts'])
            run_cmd(cmd, log_all=True, simple=True)

            # copy shared libraries to <install dir>/lib
            shlib_ext = get_shared_lib_ext()
            libdir = os.path.join(self.installdir, 'lib')
            try:
                for lib in glob.glob('libbz2.%s.*' % shlib_ext):
                    # only way to copy a symlink is to check for it,
                    # cfr. http://stackoverflow.com/questions/4847615/copying-a-symbolic-link-in-python
                    if os.path.islink(lib):
                        os.symlink(os.readlink(lib), os.path.join(libdir, lib))
                    else:
                        shutil.copy2(lib, libdir)
            except OSError, err:
                raise EasyBuildError("Copying shared libraries to installation dir %s failed: %s", libdir, err)

            # create symlink libbz2.so >> libbz2.so.1.0.6
            try:
                cwd = os.getcwd()
                os.chdir(libdir)
                os.symlink('libbz2.%s.%s' % (shlib_ext, self.version), 'libbz2.%s' % shlib_ext)
                os.chdir(cwd)
            except OSError, err:
                raise EasyBuildError("Creating symlink for libbz2.so failed: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for bzip2."""
        libs = ['lib/libbz2.a']
        if self.cfg['with_shared_libs']:
            shlib_ext = get_shared_lib_ext()
            libs.extend(['lib/libbz2.%s.%s' % (shlib_ext, self.version), 'lib/libbz2.%s' % shlib_ext])

        custom_paths = {
            'files': ['bin/b%s' % x for x in ['unzip2', 'zcat', 'zdiff', 'zgrep', 'zip2', 'zip2recover', 'zmore']] +
                     ['include/bzlib.h'] + libs,
            'dirs': [],
        }
        super(EB_bzip2, self).sanity_check_step(custom_paths=custom_paths)
