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
EasyBuild support for ARB, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.environment import setvar
from easybuild.tools.run import run_cmd


class EB_ARB(ConfigureMake):
    """Support for building and installing ARB."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ARB, specify building in install dir."""
        super(EB_ARB, self).__init__(*args, **kwargs)

        self.build_in_installdir = True
        self.subdir = 'UNKNOWN'

    def configure_step(self):
        """No separate configure step for ARB."""
        self.subdir = os.path.basename(self.cfg['start_dir'].strip(os.path.sep))

    def build_step(self):
        """Build ARB by running make."""
        # set/extend required environment variables
        path = os.environ.get('PATH', '')
        ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
        setvar('ARBHOME', os.getcwd())
        setvar('PATH', os.pathsep.join([
            os.path.join(self.cfg['start_dir'], 'bin'),
            path,
        ]))
        setvar('LD_LIBRARY_PATH', os.pathsep.join([
            os.path.join(self.cfg['start_dir'], 'lib'),
            os.path.join(self.cfg['start_dir'], 'LIBLINK'),
            ld_library_path,
        ]))

        # update make options
        # no OpenGL support, verbose, 64-bit
        self.cfg.update('buildopts', 'all OPENGL=0 V=1 ARB_64=1')

        # run 'make' without arguments to configure build, ignore non-zero exit code
        (out, ec) = run_cmd("make", simple=False, log_all=False, log_ok=False)
        self.log.debug("Command 'make' used to configure exited with exitcode %s (ignored) and output:\n%s" % (ec, out))

        super(EB_ARB, self).build_step()

    def install_step(self):
        """No installation step, ARB was built in installdir"""
        pass

    def make_module_req_guess(self):
        """Specify correct LD_LIBRARY_PATH and CPATH for this installation."""
        guesses = super(EB_ARB, self).make_module_req_guess()
        guesses.update({
            'CPATH': [os.path.join(self.subdir, "include")],
            'PATH': [os.path.join(self.subdir, "bin")],
            'LD_LIBRARY_PATH': [os.path.join(self.subdir, "lib")],
        })
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for ARB."""
        custom_paths = {
            'files': [os.path.join(self.subdir, "bin/arb") ],
            'dirs': [os.path.join(self.subdir, x) for x in ["lib"]],
        }
        super(EB_ARB, self).sanity_check_step(custom_paths=custom_paths)
