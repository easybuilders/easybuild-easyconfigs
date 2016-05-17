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
EasyBuild support for SHRiMP, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import shutil

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_SHRiMP(ConfigureMake):
    """Support for building SHRiMP."""

    def configure_step(self):
        """Add openmp compilation flag to CXX_FLAGS."""

        cxxflags = os.getenv('CXXFLAGS')

        env.setvar('CXXFLAGS', "%s %s" % (cxxflags, self.toolchain.get_flag('openmp')))

    def install_step(self):
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
            raise EasyBuildError("Failed to copy files to install dir: %s", err)


    def sanity_check_step(self):
        """Custom sanity check for SHRiMP."""

        custom_paths = {
                        'files':['bin/%s' % x for x in ["fasta2fastq", "gmapper", "mergesam",
                                                        "prettyprint", "probcalc", "probcalc_mp",
                                                        "shrimp2sam", "shrimp_var"]],
                        'dirs':['utils']
                       }

        super(EB_SHRiMP, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Add both 'bin' and 'utils' directories to PATH."""

        guesses = super(EB_SHRiMP, self).make_module_req_guess()

        guesses.update({'PATH': ['bin', 'utils']})

        return guesses

    def make_module_extra(self):
        """Set SHRIMP_FOLDER environment variable in module."""

        txt = super(EB_SHRiMP, self).make_module_extra()

        txt += self.module_generator.set_environment('SHRIMP_FOLDER', self.installdir)

        return txt
