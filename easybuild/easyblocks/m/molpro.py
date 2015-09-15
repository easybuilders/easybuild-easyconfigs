##
# Copyright 2015-2015 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for Molpro, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import fileinput
import os
import re
import sys

from easybuild.easyblocks.generic.binary import Binary
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir, read_file
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_Molpro(ConfigureMake, Binary):
    """Support for building and installing Molpro."""

    @staticmethod
    def extra_options():
        """Define custom easyconfig parameters for Molpro."""
        # Combine extra variables from Binary and ConfigureMake easyblocks as
        # well as those needed for Molpro specifically
        extra_vars = Binary.extra_options()
        extra_vars = ConfigureMake.extra_options(extra_vars)
        extra_vars.update({
            'precompiled_binaries': [False, "Are we installing precompiled binaries?", CUSTOM],
        })
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, initialize class variables specific to Molpro and check on license token."""
        super(EB_Molpro, self).__init__(*args, **kwargs)

        self.full_prefix = ''  # no None, to make easyblock compatible with --module-only
        self.orig_launcher = None

        self.cleanup_token_symlink = False
        self.license_token = os.path.join(os.path.expanduser('~'), '.molpro', 'token')

    def extract_step(self):
        if self.cfg['precompiled_binaries']:
            Binary.extract_step(self)
        else:
            ConfigureMake.extract_step(self)

    def configure_step(self):
        """Custom configuration procedure for Molpro: use 'configure -batch'."""

        if not os.path.isfile(self.license_token):
            if self.cfg['license_file'] is not None and os.path.isfile(self.cfg['license_file']):
                # put symlink in place to specified license file in $HOME/.molpro/token
                # other approaches (like defining $MOLPRO_KEY) don't seem to work
                self.cleanup_token_symlink = True
                mkdir(os.path.dirname(self.license_token))
                try:
                    os.symlink(self.cfg['license_file'], self.license_token)
                    self.log.debug("Symlinked %s to %s", self.cfg['license_file'], self.license_token)
                except OSError, err:
                    raise EasyBuildError("Failed to create symlink for license token at %s", self.license_token)

            else:
                self.log.warning("No licence token found at either {0} or via 'license_file'".format(self.license_token))
        
        # Only do the rest of the configuration if we're building from source 
        if not self.cfg['precompiled_binaries']:

            # installation prefix
            self.cfg.update('configopts', "-prefix %s" % self.installdir)

            # compilers

            # compilers & MPI
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', "-%s -%s" % (os.environ['CC_SEQ'], os.environ['F90_SEQ']))
                if 'MPI_INC_DIR' in os.environ:
                    self.cfg.update('configopts', "-mpp -mppbase %s" % os.environ['MPI_INC_DIR'])
                else:
                    raise EasyBuildError("$MPI_INC_DIR not defined")
            else:
                self.cfg.update('configopts', "-%s -%s" % (os.environ['CC'], os.environ['F90']))

            # BLAS/LAPACK
            if 'BLAS_LIB_DIR' in os.environ:
                self.cfg.update('configopts', "-blas -blaspath %s" % os.environ['BLAS_LIB_DIR'])
            else:
                raise EasyBuildError("$BLAS_LIB_DIR not defined")

            if 'LAPACK_LIB_DIR' in os.environ:
                self.cfg.update('configopts', "-lapack -lapackpath %s" % os.environ['LAPACK_LIB_DIR'])
            else:
                raise EasyBuildError("$LAPACK_LIB_DIR not defined")

            # 32 vs 64 bit
            if self.toolchain.options.get('32bit', None):
                self.cfg.update('configopts', '-i4')
            else:
                self.cfg.update('configopts', '-i8')

            run_cmd("./configure -batch %s" % self.cfg['configopts'])

            cfgfile = os.path.join(self.cfg['start_dir'], 'CONFIG')
            cfgtxt = read_file(cfgfile)

            # determine original LAUNCHER value
            launcher_regex = re.compile('^LAUNCHER=(.*)$', re.M)
            res = launcher_regex.search(cfgtxt)
            if res:
                self.orig_launcher = res.group(1)
                self.log.debug("Found original value for LAUNCHER: %s", self.orig_launcher)
            else:
                raise EasyBuildError("Failed to determine LAUNCHER value")

            # determine full installation prefix
            prefix_regex = re.compile('^PREFIX=(.*)$', re.M)
            res = prefix_regex.search(cfgtxt)
            if res:
                self.full_prefix = res.group(1)
                self.log.debug("Found full installation prefix: %s", self.full_prefix)
            else:
                raise EasyBuildError("Failed to determine full installation prefix")

            # determine MPI launcher command that can be used during build/test
            # obtain command with specific number of cores (required by mpi_cmd_for), then replace that number with '%n'
            launcher = self.toolchain.mpi_cmd_for('%x', self.cfg['parallel'])
            launcher = launcher.replace(' %s' % self.cfg['parallel'], ' %n')

            # patch CONFIG file to change LAUNCHER definition, in order to avoid having to start mpd
            for line in fileinput.input(cfgfile, inplace=1, backup='.orig'):
                line = re.sub(r"^(LAUNCHER\s*=\s*).*$", r"\1 %s" % launcher, line)
                sys.stdout.write(line)

            # reread CONFIG and log contents
            cfgtxt = read_file(cfgfile)
            self.log.info("Contents of CONFIG file:\n%s", cfgtxt)

    def build_step(self):
        if not self.cfg['precompiled_binaries']:
            super(EB_Molpro, self).build_step()

    def test_step(self):
        
        # Only bother to check if the licence token is available
        if os.path.isfile(self.license_token) and not self.cfg['precompiled_binaries']:
        
            """Custom test procedure for Molpro: make quicktest, make test."""
            # check 'main routes' only
            run_cmd("make quicktest")

            # extensive test
            run_cmd("make MOLPRO_OPTIONS='-n%s' test" % self.cfg['parallel'])

    def install_step(self):
        """
        Custom install procedure for Molpro:
        * put license token in place in $installdir/.token
        * run 'make tuning'
        * install with 'make install'
        """

        if self.cfg['precompiled_binaries']:
            """Build by running the command with the inputfiles"""
            try:
                os.chdir(self.cfg['start_dir'])
            except OSError, err:
                raise EasyBuildError("Failed to move (back) to %s: %s", self.cfg['start_dir'], err)

            for src in self.src:
                # determine command to use
                # If we need to, we can always re-use the strategy
                # in the CmdCp easyblock down the track -- but for
                # now, let's keep it simple
                cmd = "{0} -batch -instbin {1}/bin -instlib {1}/lib".format(os.path.join(".", src['name']),self.installdir)
                # Questions whose text must match exactly as asked
                qa = {
                        "Please give your username for accessing molpro\n": '',
                        "Please give your password for accessing molpro\n": '',
                }
                # Questions whose text may be matched as a regular expression
                stdqa = {
                        r"Enter installation directory for executable files \[.*\]\n": "{0}/bin".format(self.installdir),
                        r"Enter installation directory for library files \[.*\]\n": "{0}/lib".format(self.installdir),
                        r"directory .* does not exist, try to create [Y]/n\n": '',
                }
                run_cmd_qa(cmd, qa=qa, std_qa=stdqa, log_all=True, simple=True)

        else:

            if os.path.isfile(self.license_token):
                run_cmd("make tuning")

            super(EB_Molpro, self).install_step()

            # put original LAUNCHER definition back in place in bin/molpro that got installed,
            # since the value used during installation point to temporary files
            for line in fileinput.input(os.path.join(self.full_prefix, 'bin', 'molpro'), inplace=1):
                line = re.sub(r"^(LAUNCHER\s*=\s*).*$", r"\1 %s" % self.orig_launcher, line)
                sys.stdout.write(line)

        if self.cleanup_token_symlink:
            try:
                os.remove(self.license_token)
                self.log.debug("Symlink to license token %s removed", self.license_token)
            except OSError, err:
                raise EasyBuildError("Failed to remove %s: %s", self.license_token, err)

    def make_module_req_guess(self):
        """Customize $PATH guesses for Molpro module."""
        guesses = super(EB_Molpro, self).make_module_req_guess()
        guesses.update({
            'PATH': [os.path.join(os.path.basename(self.full_prefix), x) for x in ['bin', 'utilities']],
        })
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for Molpro."""
        prefix_subdir = os.path.basename(self.full_prefix)
        files_to_check = ['bin/molpro']
        dirs_to_check = []
        if not self.cfg['precompiled_binaries']:
            files_to_check.extend(['bin/molpro.exe'])
            dirs_to_check.extend(['doc', 'examples', 'utilities'])

        custom_paths = {
            'files': [os.path.join(prefix_subdir, x) for x in files_to_check],
            'dirs': [os.path.join(prefix_subdir, x) for x in dirs_to_check],
        }
        super(EB_Molpro, self).sanity_check_step(custom_paths=custom_paths)
