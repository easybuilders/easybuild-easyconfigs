"""
EasyBlock to build CHARMM

@author: Ward Poelmans (Ghent University)
@todo add support for more QC software (q-chem, gamess, ...)
"""

import os
import shutil

import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version


class EB_CHARMM(EasyBlock):
    """
    Block to build CHARMM
    """

    @staticmethod
    def extra_options():
        """Add extra easyconfig parameters custom to CHARMM."""
        extra_vars = [
            ('build_options', [["FULL"], "Specify the options to the build script", CUSTOM]),
            ('system_size', ["medium", "Specify the supported systemsize: huge, xxlarge, xlarge, large, medium (default), small, xsmall, reduce", CUSTOM]),

        ]
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        # Clean out old dir but don't create new one
        self.cfg['dontcreateinstalldir'] = True

        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            self.arch = "em64t"
        else:
            self.arch = "gnu"

        super(EB_CHARMM, self).make_dir(self.installdir, True, dontcreateinstalldir=True)

    def build_step(self, verbose=False):
        """
        Start the actual build
        """
        self.log.info("Building for size: %s" % self.cfg['system_size'])
        self.log.info("Build options from the easyconfig: %s" % self.cfg['build_options'])

        build_options = ' '.join(self.cfg['build_options'])

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

        if get_software_root("Gaussian") and 'g09' in get_software_version('Gaussian'):
            self.log.info("Using g09")
            build_options += " G09"
        else:
            self.log.info("Not using g09")

        if self.toolchain.options.get('usempi', None):
            self.log.info("Using MPI")
            build_options += " M MPIF90"

        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            build_options += " IFORT"

        cmd = "./install.com %s %s %s" % (self.arch, self.cfg['system_size'], build_options)

        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)

        return out

    def test_step(self):
        if self.toolchain.options.get('usempi', None):
            cmd = "./test.com M %s %s" % (self.cfg['parallel'], self.arch)
        else:
            cmd = "./test.com %s" % self.arch
        os.chdir("test")
        (out, _) = run_cmd(cmd, log_all=True, simple=False)
        os.chdir("..")

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
        self.log.info("Copying CHARMM dir %s to %s" % (self.cfg['start_dir'], self.installdir))
        try:
            shutil.copytree(self.cfg['start_dir'], self.installdir)
        except OSError, err:
            self.log.error("Failed to copy CHARMM dir to install dir: %s" % err)

    def make_module_extra(self):
        """Set correct PATH for CHARMM module."""
        txt = super(EB_CHARMM, self).make_module_extra()

        if self.toolchain.options.get('usempi', None):
            txt += self.moduleGenerator.prepend_paths('PATH', ['exec/%s_M' % self.arch])
        else:
            txt += self.moduleGenerator.prepend_paths('PATH', ['exec/%s' % self.arch])

        return txt
