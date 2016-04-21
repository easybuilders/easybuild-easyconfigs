##
# This is an easyblock for EasyBuild, see https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2015 Juelich Supercomputing Centre, Germany
# Authors::   Bernd Mohr <b.mohr@fz-juelich.de>
#             Markus Geimer <m.geimer@fz-juelich.de>
# License::   3-clause BSD
#
# This work is based on experiences from the UNITE project
# http://apps.fz-juelich.de/unite/
##
"""
EasyBuild support for building and installing PDT, implemented as an easyblock

@author Bernd Mohr (Juelich Supercomputing Centre)
@author Markus Geimer (Juelich Supercomputing Centre)
"""

import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
import easybuild.tools.toolchain as toolchain
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_PDT(ConfigureMake):
    """Support for building/installing PDT."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for PDT."""
        super(EB_PDT, self).__init__(*args, **kwargs)

        out, _ = run_cmd("uname -m", simple=False)
        self.machine = out.strip()
        self.log.info("Using '%s' as machine label", self.machine)

    def prepare_step(self):
        """Custom prepare step for PDT."""
        super(EB_PDT, self).prepare_step()

        # create install directory and make sure it does not get cleaned up again in the install step;
        # the first configure iteration already puts things in place in the install directory,
        # so that shouldn't get cleaned up afterwards...
        self.log.info("Creating install dir %s before starting configure-build-install iterations", self.installdir)
        self.make_installdir()
        self.cfg['keeppreviousinstall'] = True

    def configure_step(self):
        """Custom configuration procedure for PDT."""
        # custom prefix option for configure command
        self.cfg['prefix_opt'] = '-prefix='

        # determine values for compiler flags to use
        known_compilers = {
            toolchain.DUMMY: '-GNU',  # Assume that dummy toolchain uses a system-provided GCC
            toolchain.GCC: '-GNU',
            toolchain.INTELCOMP: '-icpc',
        }
        comp_fam = self.toolchain.comp_family()
        if comp_fam in known_compilers:
            compiler_opt = known_compilers[comp_fam]
        else:
            raise EasyBuildError("Compiler family not supported yet: %s" % comp_fam)
        self.cfg.update('configopts', compiler_opt)

        super(EB_PDT, self).configure_step()

    def build_step(self):
        """Custom build procedure for PDT."""
        # The PDT build is triggered by 'make install', thus skip the 'make' step
        pass

    def sanity_check_step(self):
        """Custom sanity check for PDT."""
        custom_paths = {
            'files': [os.path.join(self.machine, 'bin', 'cparse'),
                      os.path.join(self.machine, 'include', 'pdb.h'),
                      os.path.join(self.machine, 'lib', 'libpdb.a')],
            'dirs': [],
        }
        super(EB_PDT, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for environment variables (PATH, ...) for PDT."""
        guesses = super(EB_PDT, self).make_module_req_guess()
        guesses.update({
            'PATH': [os.path.join(self.machine, 'bin')],
            'LD_LIBRARY_PATH': [os.path.join(self.machine, 'lib')],
        })
        return guesses
