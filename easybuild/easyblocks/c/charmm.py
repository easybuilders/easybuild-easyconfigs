##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing CHARMM, implemented as an easyblock

@author: Ward Poelmans (Ghent University)
"""
# TODO: add support for more QC software (q-chem, gamess, ...)

import shutil

from easybuild.framework.easyconfig import CUSTOM
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd
import easybuild.tools.toolchain as toolchain

# Possible systemsizes for CHARMM
KNOWN_SYSTEM_SIZES = ['huge', 'xxlarge', 'xlarge', 'large', 'medium', 'small', 'xsmall', 'reduce']


class EB_CHARMM(EasyBlock):
    """
    Support for building/installing CHARMM
    """

    @staticmethod
    def extra_options():
        """Add extra easyconfig parameters custom to CHARMM."""
        extra_vars = {
            'build_options': ["FULL", "Specify the options to the build script", CUSTOM],
            'system_size': ["medium", "Specify the supported systemsize: %s" % ', '.join(KNOWN_SYSTEM_SIZES), CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for CHARMM."""
        super(EB_CHARMM, self).__init__(*args, **kwargs)
        self.arch = 'UNKNOWN'

    def configure_step(self):
        # Clean out old dir but don't create new one
        self.cfg['dontcreateinstalldir'] = True

        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            self.arch = "em64t"
        else:
            self.arch = "gnu"

        super(EB_CHARMM, self).make_dir(self.installdir, True, dontcreateinstalldir=True)

    def build_step(self, verbose=False):
        """Start the actual build"""
        if self.cfg['system_size'] not in KNOWN_SYSTEM_SIZES:
            raise EasyBuildError("Unknown system size '%s' specified, known: %s", self.cfg['system_size'], KNOWN_SYSTEM_SIZES)

        self.log.info("Building for size: %s" % self.cfg['system_size'])
        self.log.info("Build options from the easyconfig: %s" % self.cfg['build_options'])
        build_options = self.cfg['build_options']

        # FFTW and MKL are mutally exclusive
        if get_software_root("FFTW"):
            self.log.info("Using FFTW")
            build_options += " FFTW"
        else:
            self.log.info("Not using FFTW")
            if get_software_root("imkl"):
                self.log.info("Using the MKL")
                build_options += " MKL"
            else:
                self.log.info("Not using MKL")

        # Currently, only support for g09 added
        if get_software_root("Gaussian") and 'g09' in get_software_version('Gaussian'):
            self.log.info("Using g09")
            build_options += " G09"
        else:
            self.log.info("Not using g09")

        if self.toolchain.options.get('usempi', None):
            self.log.info("Using MPI")
            # M means use MPI and MPIF90 means let mpif90 handle all MPI stuff
            build_options += " M MPIF90"

        # By default, CHARMM uses gfortran. We need to specify if we want ifort
        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            build_options += " IFORT"

        cmd = "./install.com %s %s %s" % (self.arch, self.cfg['system_size'], build_options)
        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)
        return out

    def test_step(self):
        """Run the testsuite"""
        if self.toolchain.options.get('usempi', None):
            cmd = "cd test && ./test.com M %s %s" % (self.cfg['parallel'], self.arch)
        else:
            cmd = "cd test && ./test.com %s" % self.arch
        (out, _) = run_cmd(cmd, log_all=True, simple=False)
        return out

    def sanity_check_step(self):
        """Custom sanity check for CHARMM."""
        custom_paths = {
            'files': [],
            'dirs': [],
        }
        if self.toolchain.options.get('usempi', None):
            custom_paths['files'].append('exec/%s_M/charmm' % self.arch)
        else:
            custom_paths['files'].append('exec/%s/charmm' % self.arch)
        super(EB_CHARMM, self).sanity_check_step(custom_paths=custom_paths)

    def install_step(self):
        """Copy the build directory to the install path"""
        self.log.info("Copying CHARMM dir %s to %s" % (self.cfg['start_dir'], self.installdir))
        try:
            shutil.copytree(self.cfg['start_dir'], self.installdir)
        except OSError, err:
            raise EasyBuildError("Failed to copy CHARMM dir to install dir: %s", err)

    def make_module_req_guess(self):
        """Custom guesses for environment variable PATH for CHARMM."""
        guesses = super(EB_CHARMM, self).make_module_req_guess()
        if self.toolchain.options.get('usempi', None):
            suffix = "_M"
        else:
            suffix = ""
        guesses.update({
            'PATH': ['exec/%s%s' % (self.arch, suffix)],
        })
        return guesses
