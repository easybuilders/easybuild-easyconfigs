##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
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
EasyBuild support for METIS, implemented as an easyblock
"""
import os
import shutil
from distutils.version import LooseVersion

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, mkdir


class EB_METIS(Application):
    """Support for building and installing METIS."""

    def configure(self, *args, **kwargs):
        """Configure build using 'make config' (only for recent versions (>= v5))."""

        if LooseVersion(self.version()) >= LooseVersion("5"):

            cmd = "make config prefix=%s" % self.installdir
            run_cmd(cmd, log_all=True, simple=True)

    def make(self):
        """Add make options before building."""

        self.updatecfg('makeopts', 'LIBDIR=""')

        if self.toolkit().opts['pic']:
            self.updatecfg('makeopts', 'CC="$CC -fPIC"')

        Application.make(self)

    def make_install(self):
        """
        Install by manually copying files to install dir, for old versions,
        or by running 'make install' for new versions.
        
        Create symlinks where expected by other applications
        (in Lib instead of lib)
        """

        if LooseVersion(self.version()) < LooseVersion("5"):

            libdir = os.path.join(self.installdir, 'lib')
            mkdir(libdir)

            includedir = os.path.join(self.installdir, 'include')
            mkdir(includedir)

            # copy libraries
            try:
                src = os.path.join(self.getcfg('startfrom'), 'libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except OSError, err:
                self.log.error("Copying file libmetis.a to lib dir failed: %s" % err)

            # copy include files
            try:
                for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                    src = os.path.join(self.getcfg('startfrom'), 'Lib', f)
                    dst = os.path.join(includedir, f)
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0755)
            except OSError, err:
                self.log.error("Copying file metis.h to include dir failed: %s" % err)

            # other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
            # and header files in the Lib directory (capital L). The following symlinks are hence created.
            try:
                Libdir = os.path.join(self.installdir, 'Lib')
                os.symlink(libdir, Libdir)
                for f in ['defs.h', 'macros.h', 'metis.h', 'proto.h', 'rename.h', 'struct.h']:
                    os.symlink(os.path.join(includedir, f), os.path.join(libdir, f))
            except OSError, err:
                self.log.error("Something went wrong during symlink creation: %s" % err)

        else:
            Application.make_install(self)

    def sanitycheck(self):
        """Custom sanity check for METIS (more extensive for recent version (>= v5))"""

        if not self.getcfg('sanityCheckPaths'):

            binfiles = []
            if LooseVersion(self.version()) > LooseVersion("5"):
                binfiles += ["cmpfillin", "gpmetis", "graphchk", "m2gmetis", "mpmetis", "ndmetis"]

            incfiles = ["metis.h"]
            if LooseVersion(self.version()) < LooseVersion("5"):
                incfiles += ["defs.h", "macros.h", "proto.h", "rename.h", "struct.h"]

            dirs = []
            if LooseVersion(self.version()) < LooseVersion("5"):
                dirs += ["Lib"]

            self.setcfg('sanityCheckPaths', {
                                             'files': ['bin/%s' % x for x in binfiles] +
                                                      ['include/%s' % x for x in incfiles] +
                                                      ['lib/libmetis.a'],
                                             'dirs' : dirs
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
