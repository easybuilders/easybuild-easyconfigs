## 
# Copyright 2012 Kenneth Hoste
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
EasyBuild support for SHRiMP, implemented as an easyblock
"""
import glob
import os
import shutil

import easybuild.tools.environment as env
from easybuild.framework.application import Application


class EB_SHRiMP(Application):
    """Support for building SHRiMP."""

    def configure(self):
        """Add openmp compilation flag to CXX_FLAGS."""

        cxxflags = os.getenv('CXXFLAGS')

        env.set('CXXFLAGS', "%s %s" % (cxxflags, self.toolkit().get_openmp_flag()))

    def make_install(self):
        """Install SHRiMP by copying files to install dir, and fix permissions."""

        try:
            for d in ["bin", "utils"]:
                shutil.copytree(d, os.path.join(self.installdir, d))

            cwd = os.getcwd()

            os.chdir(os.path.join(self.installdir, "utils"))
            for f in glob.glob("*.py"):
                self.log.info("Fixing permissions of %s in utils" % f)
                os.chmod(f, 0755)

            os.chdir(cwd)

        except OSError, err:
            self.log.error("Failed to copy files to install dir: %s" % err)


    def sanitycheck(self):
        """Custom sanity check for SHRiMP."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files':['bin/%s' % x for x in ["fasta2fastq",
                                                                             "gmapper",
                                                                             "mergesam",
                                                                             "prettyprint",
                                                                             "probcalc",
                                                                             "probcalc_mp",
                                                                             "shrimp2sam",
                                                                             "shrimp_var"]
                                                      ],
                                             'dirs':['utils']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def make_module_req_guess(self):
        """Add both 'bin' and 'utils' directories to PATH."""

        guesses = Application.make_module_req_guess(self)

        guesses.update({'PATH': ['bin', 'utils']})

        return guesses

    def make_module_extra(self):
        """Set SHRIMP_FOLDER environment variable in module."""

        txt = Application.make_module_extra(self)

        txt += self.moduleGenerator.setEnvironment('SHRIMP_FOLDER', "$root")

        return txt
