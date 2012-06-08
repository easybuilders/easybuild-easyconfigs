##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
import os
import shutil
from distutils.version import LooseVersion
from easybuild.framework.application import Application

class MrBayes(Application):

    def configure(self):

        self.updatecfg('makeopts', 'CC="%s" OPTFLAGS="%s"' % (os.getenv('MPICC'), os.getenv('CFLAGS')))

        if LooseVersion(self.version()) >= LooseVersion("3.2"):
            self.setcfg('startfrom', 'src')
            cmd = "autoconf"
            run_cmd(cmd)

            if os.getenv('SOFTROOTBEAGLE'):
                self.updatecfg('configopts', '--with-beagle=%s' % os.getenv('SOFTROOTBEAGLE'))
            else:
                self.log.error("BEAGLE module not loaded?")

            if self.tk.opts['usempi']:
                self.updatecfg('configopts', '--enable-mpi')

            Application.configure(self)
        else:
            self.updatecfg('makeopts', 'MPI=yes')

    def make_install(self):
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

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["bin/mb"],
                                            'dirs':[]
                                            }
                        )

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
