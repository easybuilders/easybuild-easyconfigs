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
EasyBuild support for ABAQUS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from distutils.version import LooseVersion


class EB_ABAQUS(Binary):
    """Support for installing ABAQUS."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ABAQUS."""
        super(EB_ABAQUS, self).__init__(*args, **kwargs)
        self.replayfile = None

    def extract_step(self):
        """Use default extraction procedure instead of the one for the Binary easyblock."""
        EasyBlock.extract_step(self)

    def configure_step(self):
        """Configure ABAQUS installation."""
        try:
            self.replayfile = os.path.join(self.builddir, "installer.properties")
            txt = '\n'.join([
                "INSTALLER_UI=SILENT",
                "USER_INSTALL_DIR=%s" % self.installdir,
                "MAKE_DEF_VER=true",
                "DOC_ROOT=UNDEFINED",
                "DOC_ROOT_TYPE=false",
                "DOC_ROOT_ESCAPED=UNDEFINED",
                "ABAQUSLM_LICENSE_FILE=@abaqusfea",
                "LICENSE_SERVER_TYPE=FLEXNET",
                "PRODUCT_NAME=Abaqus %s" % self.version,
                "TMPDIR=%s" % self.builddir,
                "INSTALL_MPI=1",
            ])
            f = file(self.replayfile, "w")
            f.write(txt)
            f.close()
        except IOError, err:
            raise EasyBuildError("Failed to create install properties file used for replaying installation: %s", err)

    def install_step(self):
        """Install ABAQUS using 'setup'."""
        os.chdir(self.builddir)
        if self.cfg['install_cmd'] is None:
            self.cfg['install_cmd'] = "%s/%s-%s/setup" % (self.builddir, self.name, self.version.split('-')[0])
            self.cfg['install_cmd'] += " -replay %s" % self.replayfile
            if LooseVersion(self.version) < LooseVersion("6.13"):
                self.cfg['install_cmd'] += " -nosystemcheck"
        super(EB_ABAQUS, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for ABAQUS."""
            
        verparts = self.version.split('-')[0].split('.')
        custom_paths = {
            'files': [os.path.join("Commands", "abaqus")],
            'dirs': ["%s-%s" % ('.'.join(verparts[0:2]), verparts[2])]
        }
        custom_commands = [('abaqus', 'information=all')]
        super(EB_ABAQUS, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_req_guess(self):
        """Update PATH guesses for ABAQUS."""

        guesses = super(EB_ABAQUS, self).make_module_req_guess()
        guesses.update({
            'PATH': ['Commands'],
        })
        return guesses
