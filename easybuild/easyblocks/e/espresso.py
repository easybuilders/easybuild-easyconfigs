##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Authors::   Josh Berryman <the.real.josh.berryman@gmail.com>, Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-80.html
##
"""
EasyBuild support for building and installing ESPResSo, implemented as an easyblock

@author: Josh Berryman <the.real.josh.berryman@gmail.com>
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd


class EB_ESPResSo(ConfigureMake):
    """Support for building/installing ESPResSo, parallel version."""

    def __init__(self, *args, **kwargs):
        """Specify to build in install dir."""
        super(EB_ESPResSo, self).__init__(*args, **kwargs)

        self.build_in_installdir = True
        self.install_subdir = '%s-%s' % (self.name.lower(), self.version)

    @staticmethod
    def extra_options():
        extra_vars = {
            'runtest': [True, "Run ESPResSo tests.", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def test_step(self):
        """Custom built-in test procedure for ESPResSo, parallel version."""

        if self.cfg['runtest']:
            cmd = './runtest.sh -p 2 *.tcl'  
            (out, ec) = run_cmd(cmd, simple=False, log_all=False, log_ok=False, path="testsuite")

            if ec:
                # ESPResSo fails many of its tests in version 3.1.1, and the test script itself is buggy
                # so, just provide output in log file, but ignore things if it fails
                self.log.warning("ESPResSo test failed (exit code: %s): %s" % (ec, out))
            else:
                self.log.info("Successful ESPResSo test completed: %s" % out)

    def install_step(self):
        """Build is done in install dir, so no separate install step."""
        pass 

    def sanity_check_step(self):
        """Custom sanity check for ESPResSo."""

        custom_paths = {
                        'files' : [os.path.join(self.install_subdir, 'Espresso')],
                        'dirs'  : [os.path.join(self.install_subdir, x) for x in ['samples', 'scripts', 'tools']],
                       }

        super(EB_ESPResSo, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Customize PATH for ESPResSo."""

        guesses = super(EB_ESPResSo, self).make_module_req_guess()

        guesses.update({'PATH': [self.install_subdir]})

        return guesses
