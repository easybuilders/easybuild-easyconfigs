##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
# Copyright 2012 Andy Georges
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
EasyBuild support for building and installing MrBayes, implemented as an easyblock
"""

import os
import shutil
from distutils.version import LooseVersion

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd


class MrBayes(Application):
    """Support for building/installing MrBayes."""

    def configure(self):
        """Configure build: <single-line description how this deviates from standard configure>"""

        # set generic make options
        self.updatecfg('makeopts', 'CC="%s" OPTFLAGS="%s"' % (os.getenv('MPICC'), os.getenv('CFLAGS')))

        if LooseVersion(self.version()) >= LooseVersion("3.2"):

            # set correct startfrom dir, and change into it
            self.setcfg('startfrom', os.path.join(self.getcfg('startfrom'),'src'))
            try:
              os.chdir(self.getcfg('startfrom'))
            except OSError, err:
              self.log.error("Failed to change to correct source dir %s: %s" % (self.getcfg('startfrom'), err))

            # run autoconf to generate configure script
            cmd = "autoconf"
            run_cmd(cmd)

            # set config opts
            if os.getenv('SOFTROOTBEAGLE'):
                self.updatecfg('configopts', '--with-beagle=%s' % os.getenv('SOFTROOTBEAGLE'))
            else:
                self.log.error("BEAGLE module not loaded?")

            if self.tk.opts['usempi']:
                self.updatecfg('configopts', '--enable-mpi')

            # configure
            Application.configure(self)
        else:

            # no configure script prior to v3.2
            self.updatecfg('makeopts', 'MPI=yes')

    def make_install(self):
        """Install by copying bniaries to install dir."""

        bindir = os.path.join(self.installdir, 'bin')
        os.makedirs(bindir)

        for exe in ['mb']:
            src = os.path.join(self.getcfg('startfrom'), exe)
            dst = os.path.join(bindir, exe)
            try:
                shutil.copy2(src, dst)
                self.log.info("Successfully copied %s to %s" % (src, dst))
            except (IOError,OSError), err:
                self.log.error("Failed to copy %s to %s (%s)" % (src, dst, err))

    def sanitycheck(self):
        """Custom sanity check for MrBayes."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["bin/mb"],
                                            'dirs':[]
                                            }
                        )

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

