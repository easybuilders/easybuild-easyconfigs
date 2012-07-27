##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
EasyBuild support for cplex, implemented as an easyblock
"""
import os
import shutil
import stat
import glob
from easybuild.easyblocks.b.binary import Binary
from easybuild.tools.filetools import run_cmd_qa


class CPLEX(Binary):
    """
    Version 12.2 has a self-extratcing package with a java installer
    """

    def unpack_src(self):
        """overwrite unpack, this is non compressed binary file"""
        self.src[0]['finalpath'] = self.builddir



    def make_install(self):
        """CPLEX has an installer that prompts for information, 
        so use Q&A here
        """
        tmpdir = os.path.join(self.builddir, 'tmp')
        try:
            os.chdir(self.builddir)
            os.makedirs(tmpdir)

            os.putenv('IATEMPDIR', tmpdir)
            os.environ['IATEMPDIR'] = tmpdir

        except OSError:
            self.log.exception("Failed to change directory to %s" % self.builddir)

        # Run the source
        # - self.src: first one is source. others ignored
        src = self.src[0]['path']
        dst = os.path.join(self.builddir, self.src[0]['name'])
        try:
            shutil.copy2(src, self.builddir)
            os.chmod(dst, stat.S_IRWXU)
        except (OSError, IOError):
            self.log.exception("Couldn't copy %s to %s" % (src, self.builddir))

        cmd = "%s -i console" % dst

        qanda = {"PRESS <ENTER> TO CONTINUE:":"",
               'Press Enter to continue viewing the license agreement, or enter' \
               ' "1" to accept the agreement, "2" to decline it, "3" to print it,' \
               ' or "99" to go back to the previous screen.:':'1',
               'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :':self.installdir,
               'IS THIS CORRECT? (Y/N):':'y',
               'PRESS <ENTER> TO INSTALL:':"",
               "PRESS <ENTER> TO EXIT THE INSTALLER:":"",
               "CHOOSE LOCALE BY NUMBER:":"",
               "Choose Instance Management Option:":""
                }
        noqanda = [r'Installing\.\.\..*\n.*------.*\n\n.*============.*\n.*$']

        run_cmd_qa(cmd, qanda, no_qa=noqanda, log_all=True, simple=True)

        try:
            os.chmod(self.installdir, stat.S_IRWXU | stat.S_IXOTH | stat.S_IXGRP | stat.S_IROTH | stat.S_IRGRP)
        except OSError:
            self.log.exception("Can't set permissions on %s" % self.installdir)

    def make_module_extra(self):
        """
        Add installdir to path
        """
        os.chdir(self.installdir)
        binglob = 'cplex/bin/x86-64*'
        bins = glob.glob(binglob)
        if len(bins):
            if len(bins) > 1:
                self.log.error("More then one possible path for bin found: %s" % bins)
            else:
                bindir = bins[0]
        else:
            self.log.error("No bins found using %s in %s" % (binglob, self.installdir))
        self.bindir = bindir

        txt = Binary.make_module_extra(self)
        txt += "prepend-path\tPATH\t\t$root/%s\n" % bindir
        txt += "setenv\tCPLEX_HOME\t\t$root/cplex"
        self.log.debug("make_module_extra added %s" % txt)
        return txt

    def sanitycheck(self):
        """Custom sanity check for CPLEX"""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["%s/%s" % (self.bindir, x) for x in
                                                       ["convert", "cplex", "cplexamp"]],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Binary.sanitycheck(self)
