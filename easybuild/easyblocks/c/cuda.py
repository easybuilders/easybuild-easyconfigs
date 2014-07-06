##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2013 Cyprus Institute / CaSToRC, University of Luxembourg / LCSB, Ghent University
# Authors::   George Tsouloupas <g.tsouloupas@cyi.ac.cy>, Fotis Georgatos <fotis.georgatos@uni.lu>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-99.html
##
"""
EasyBuild support for CUDA, implemented as an easyblock

Ref: https://speakerdeck.com/ajdecon/introduction-to-the-cuda-toolkit-for-building-applications

@author: George Tsouloupas (Cyprus Institute)
@author: Fotis Georgatos (Uni.lu)
@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.tools.filetools import patch_perl_script_autoflush, run_cmd, run_cmd_qa
from distutils.version import LooseVersion


class EB_CUDA(Binary):
    """
    Support for installing CUDA.
    """

    def extract_step(self):
        """Extract installer to have more control, e.g. options, patching Perl scripts, etc."""
        execpath = self.src[0]['path']
        run_cmd("/bin/sh " + execpath + " --noexec --nox11 --target " + self.builddir)
        self.src[0]['finalpath'] = self.builddir

    def install_step(self):
        """Install CUDA using Perl install script."""

        # define how to run the installer
        # script has /usr/bin/perl hardcoded, but we want to have control over which perl is being used
        if LooseVersion(self.version) <= LooseVersion("5"):
            install_script = "install-linux.pl"
            install_script_path = os.path.join(self.builddir, install_script)
            cmd = "perl ./%s --prefix=%s" % (install_script, self.installdir)
        else:
            # the following would require to include "osdependencies = 'libglut'" because of samples
            # installparams = "-samplespath=%(x)s/samples/ -toolkitpath=%(x)s -samples -toolkit" % {'x': self.installdir}
            install_script = "cuda-installer.pl"
            installparams = "-toolkitpath=%s -toolkit" % self.installdir
            cmd = "perl ./%s -verbose -silent %s" % (install_script, installparams)

        # prepare for running install script autonomously
        qanda = {}
        stdqa = {
                 # this question is only asked if CUDA tools are already available system-wide
                 r"Would you like to remove all CUDA files under .*? (yes/no/abort): ": "no",
                }
        noqanda = [
            r"^Configuring",
            r"Installation Complete",
            r"Verifying archive integrity.*",
            r"^Uncompressing NVIDIA CUDA",
            r".* -> .*",
        ]

        # patch install script to handle Q&A autonomously
        patch_perl_script_autoflush(os.path.join(self.builddir, install_script))

        # make sure $DISPLAY is not defined, which may lead to (weird) problems
        # this is workaround for not being able to specify --nox11 to the Perl install scripts
        if 'DISPLAY' in os.environ:
            os.environ.pop('DISPLAY')

        run_cmd_qa(cmd, qanda, std_qa=stdqa, no_qa=noqanda, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for CUDA."""

        custom_paths = {
            'files': ["bin/%s" % x for x in ["fatbinary", "nvcc", "nvlink", "ptxas"]] +
                     ["%s/lib%s.so" % (x, y) for x in ["lib", "lib64"] for y in ["cublas", "cudart", "cufft",
                                                                                 "curand", "cusparse"]] +
                     ["open64/bin/nvopencc"],
            'dirs': ["include"],
        }

        super(EB_CUDA, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Specify CUDA custom values for PATH etc."""

        guesses = super(EB_CUDA, self).make_module_req_guess()

        guesses.update({
                        'PATH': ['open64/bin', 'bin'],
                        'LD_LIBRARY_PATH': ['lib64'],
                        'CPATH': ['include'],
                        'CUDA_HOME': [''],
                        'CUDA_PATH': [''],
                       })

        return guesses
