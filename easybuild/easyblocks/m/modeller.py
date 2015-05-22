##
# Copyright 2014 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for installing Modeller, implemented as an easyblock

@author: Pablo Escobar Lopez (SIB - University of Basel)
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd_qa


class EB_Modeller(EasyBlock):
    """Support for installing Modeller."""

    def configure_step(self):
        """ Skip configuration step """
        pass

    def build_step(self):
        """ Skip build step """
        pass

    def install_step(self):
        """Interactive install of Modeller."""
    
        if self.cfg['key'] is None: 
            raise EasyBuildError("Easyconfig parameter 'key' is not defined")

        cmd = "%s/Install" % self.cfg['start_dir']

        # by default modeller tries to install to $HOME/bin/modeller9.13
        # get this path to use it in the question/answer
        default_install_path = "[%s]:" % os.path.join(os.path.expanduser('~'), 'bin', 'modeller%s' % self.cfg['version'])

        qa = {
             # installer will autodetect the right arch. [3] = x86_64
             'Select the type of your computer from the list above [3]:': '',
             default_install_path: self.installdir,
             'http://salilab.org/modeller/registration.html:': self.cfg["key"],
             'Press <Enter> to begin the installation:': '',
             'Press <Enter> to continue:': ''
             }

        run_cmd_qa(cmd, qa, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for Modeller."""
        custom_paths = {
            'files': ["bin/mod%s" % self.version, "bin/modpy.sh", "bin/modslave.py"],
            'dirs': ["doc", "lib", "examples"],
        }
        super(EB_Modeller, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for environment variables (PYTHONPATH, LD_LIBRARY_PATH) for modeller."""
        guesses = super(EB_Modeller, self).make_module_req_guess()

        libspath = os.path.join(self.installdir, 'lib')
        if os.path.exists(libspath):
            libdirs = os.listdir(libspath)
            if len(libdirs) == 1:
                libdir = libdirs[0]
            else:
                raise EasyBuildError("Failed to isolate a single libdir from list of 'lib' subdirectories: %s", libdirs)

            py2libdirs = [d for d in os.listdir(os.path.join(libspath, libdir)) if d.startswith('python2')]
            if len(py2libdirs) >= 1:
                py2libdir = py2libdirs[-1]
            else:
                raise EasyBuildError("Failed to isolate latest Python lib dir from list %s", py2libdirs)

            guesses.update({
                'PYTHONPATH': [os.path.join('lib', libdir, py2libdir), "modlib"],
                'LD_LIBRARY_PATH': [os.path.join('lib', libdir)],
            })

        return guesses
