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
# https://github.com/easybuilders/easybuild
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
EasyBuild support for building and installing Mathematica, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd_qa


class EB_Mathematica(Binary):
    """Support for building/installing Mathematica."""

    @staticmethod
    def extra_options():
        """Additional easyconfig parameters custom to Mathematica."""
        extra_vars = {
            'activation_key': [None, "Activation key (expected format: 0000-0000-AAAAA)", CUSTOM],
        }
        return Binary.extra_options(extra_vars)

    def configure_step(self):
        """No configuration for Mathematica."""
        # ensure a license server is specified
        if self.cfg['license_server'] is None:
            raise EasyBuildError("No license server specified.")

    def build_step(self):
        """No build step for Mathematica."""
        pass

    def install_step(self):
        """Install Mathematica using install script."""

        # make sure $DISPLAY is not set (to avoid that installer uses GUI)
        orig_display = os.environ.pop('DISPLAY', None)

        cmd = "./%s_%s_LINUX.sh" % (self.name, self.version)
        shortver = '.'.join(self.version.split('.')[:2])
        qa_install_path = "/usr/local/Wolfram/%s/%s" % (self.name, shortver)
        qa = {
            r"Enter the installation directory, or press ENTER to select %s: >" % qa_install_path: self.installdir,
            r"Create directory (y/n)? >": 'y',
            r"or press ENTER to select /usr/local/bin: >": os.path.join(self.installdir, "bin"), 
        }
        no_qa = [
            "Now installing.*\n\n.*\[.*\].*",
        ]
        run_cmd_qa(cmd, qa, no_qa=no_qa, log_all=True, simple=True, maxhits=200)

        # add license server configuration file
        # some relevant documentation at http://reference.wolfram.com/mathematica/tutorial/ConfigurationFiles.html
        mathpass_path = os.path.join(self.installdir, 'Configuration', 'Licensing', 'mathpass')
        try:
            # append to file, to avoid overwriting anything that might be there
            f = open(mathpass_path, "a")
            f.write("!%s\n" % self.cfg['license_server'])
            f.close()
            f = open(mathpass_path, "r")
            mathpass_txt = f.read()
            f.close()
            self.log.info("Updated license file %s: %s" % (mathpass_path, mathpass_txt))
        except IOError, err:
            raise EasyBuildError("Failed to update %s with license server info: %s", mathpass_path, err)

        # restore $DISPLAY if required
        if orig_display is not None:
            os.environ['DISPLAY'] = orig_display

    def post_install_step(self):
        """Activate installation by using activation key, if provided."""
        if self.cfg['activation_key']:
            # activation key is printed by using '$ActivationKey' in Mathematica, so no reason to keep it 'secret'
            self.log.info("Activating installation using provided activation key '%s'." % self.cfg['activation_key'])
            qa = {
                r"(enter return to skip Web Activation):": self.cfg['activation_key'],
                r"In[1]:= ": 'Quit[]',
            }
            noqa = [
                '^%s %s .*' % (self.name, self.version),
                '^Copyright.*',
            ]
            run_cmd_qa(os.path.join(self.installdir, 'bin', 'math'), qa, no_qa=noqa)
        else:
            self.log.info("No activation key provided, so skipping activation of the installation.")

    def sanity_check_step(self):
        """Custom sanity check for Mathematica."""
        custom_paths = {
            'files': ['bin/mathematica'],
            'dirs': ['AddOns', 'Configuration', 'Documentation', 'Executables', 'SystemFiles'],
        }
        super(EB_Mathematica, self).sanity_check_step(custom_paths=custom_paths)
