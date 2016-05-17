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
EasyBuild support for METIS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import shutil
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir
from easybuild.tools.run import run_cmd


class EB_METIS(ConfigureMake):
    """Support for building and installing METIS."""

    def __init__(self, *args, **kwargs):
        """Define custom class variables for METIS."""
        super(EB_METIS, self).__init__(*args, **kwargs)

        self.lib_exts = []

    def configure_step(self, *args, **kwargs):
        """Configure build using 'make config' (only for recent versions (>= v5))."""

        if LooseVersion(self.version) >= LooseVersion("5"):

            cmd = "make %s config prefix=%s" % (self.cfg['configopts'], self.installdir)
            run_cmd(cmd, log_all=True, simple=True)

            if 'shared=1' in self.cfg['configopts']:
                self.lib_exts.append('so')
            else:
                self.lib_exts.append('a')

    def build_step(self):
        """Add make options before building."""

        self.cfg.update('buildopts', 'LIBDIR=""')

        if self.toolchain.options['pic']:
            self.cfg.update('buildopts', 'CC="$CC -fPIC"')

        super(EB_METIS, self).build_step()

    def install_step(self):
        """
        Install by manually copying files to install dir, for old versions,
        or by running 'make install' for new versions.
        
        Create symlinks where expected by other applications
        (in Lib instead of lib)
        """

        if LooseVersion(self.version) < LooseVersion("5"):

            libdir = os.path.join(self.installdir, 'lib')
            mkdir(libdir)

            includedir = os.path.join(self.installdir, 'include')
            mkdir(includedir)

            # copy libraries
            try:
                src = os.path.join(self.cfg['start_dir'], 'libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except OSError, err:
                raise EasyBuildError("Copying file libmetis.a to lib dir failed: %s", err)

            # copy include files
            try:
                for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                    src = os.path.join(self.cfg['start_dir'], 'Lib', f)
                    dst = os.path.join(includedir, f)
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0755)
            except OSError, err:
                raise EasyBuildError("Copying file metis.h to include dir failed: %s", err)

            # other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
            # and header files in the Lib directory (capital L). The following symlinks are hence created.
            try:
                Libdir = os.path.join(self.installdir, 'Lib')
                os.symlink(libdir, Libdir)
                for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                    os.symlink(os.path.join(includedir, f), os.path.join(libdir, f))
            except OSError, err:
                raise EasyBuildError("Something went wrong during symlink creation: %s", err)

        else:
            super(EB_METIS, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for METIS (more extensive for recent version (>= v5))"""

        binfiles = []
        if LooseVersion(self.version) > LooseVersion("5"):
            binfiles += ["cmpfillin", "gpmetis", "graphchk", "m2gmetis", "mpmetis", "ndmetis"]

        incfiles = ["metis.h"]
        if LooseVersion(self.version) < LooseVersion("5"):
            incfiles += ["defs.h", "macros.h", "proto.h", "rename.h", "struct.h"]

        dirs = []
        if LooseVersion(self.version) < LooseVersion("5"):
            dirs += ["Lib"]

        custom_paths = {
            'files': ['bin/%s' % x for x in binfiles] + ['include/%s' % x for x in incfiles] +
                     ['lib/libmetis.%s' % x for x in self.lib_exts],
            'dirs' : dirs,
        }
        super(EB_METIS, self).sanity_check_step(custom_paths=custom_paths)
