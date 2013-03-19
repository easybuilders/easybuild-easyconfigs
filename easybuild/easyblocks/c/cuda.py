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
import stat

from easybuild.easyblocks.generic.binary import Binary
from easybuild.tools.filetools import patch_perl_script_autoflush, run_cmd, run_cmd_qa
from distutils.version import LooseVersion


class EB_CUDA(Binary):
    """
    Support for installing CUDA.
    """

    def extract_step(self):
        execpath = self.src[0]['path']
        run_cmd("/bin/sh " + execpath + " --noexec --nox11 --target " + self.builddir)
        self.src[0]['finalpath'] = self.builddir

    def install_step(self):

        run_cmd("mkdir -p " + self.installdir)

        # define how to run the installer
        if LooseVersion(self.version) <= LooseVersion("5"):
            install_script = os.path.join(self.builddir, "install-linux.pl")
            cmd = install_script + " --prefix=" + self.installdir
        else:
          # the following would require to include "osdependencies = 'libglut'" because of -samples
          # installparams = "-samplespath=%s/samples/ -toolkitpath=%s -samples -toolkit" % (self.installdir, self.installdir))
          installparams = "-toolkitpath=%s -toolkit" % self.installdir
          install_script = os.path.join(self.builddir, "cuda-installer.pl")
          cmd = install_script + " -verbose -silent " + installparams

        qanda = {}
        stdqa = {
                 "Would you like to remove all CUDA files under .*? (yes/no/abort): ": "no",
                 }
        noqanda = [r"Installation Complete"]

        # patch install script to handle Q&A autonomously
        patch_perl_script_autoflush(install_script)

        run_cmd_qa(cmd, qanda, std_qa=stdqa, no_qa=noqanda, log_all=True, simple=True)

	# FIXME (kehoste): what is this about? why chmod the installdir?!? FG: probably obsolete, need to check
        try:
            os.chmod(self.installdir, stat.S_IRWXU | stat.S_IXOTH | stat.S_IXGRP | stat.S_IROTH | stat.S_IRGRP)
        except OSError, err:
            self.log.exception("Can't set permissions on %s: %s" % (self.installdir, err))

    def sanity_check_step(self):
        """Custom sanity check for CUDA."""

        custom_paths = {
            'files': ["bin/%s" % x for x in ["fatbinary", "nvcc", "nvlink", "ptxas"]] +
                     ["%s/lib%s.so" % (x, y) for x in ["lib", "lib64"] for y in ["cublas", "cudart", "cufft",
                                                                                 "curand", "cusparse", "npp"]] +
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
