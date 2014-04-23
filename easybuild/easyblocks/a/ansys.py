##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for installing ANSYS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Bart Verleye (Auckland)
"""


import shutil
import os
import stat

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd, rmtree2
from easybuild.tools.filetools import adjust_permissions


class EB_ANSYS(EasyBlock):
    """Support for installing ANSYS."""


    def configure_step(self):
        """No configuration for ANSYS."""
        pass

    def build_step(self):
        """No building for ANSYS."""
        pass

    def install_step(self):
        """Custom install procedure for ANSYS."""
        
        cmd = "./INSTALL -noroot -silent -install_dir %s %s" % (self.installdir,self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        adjust_permissions(self.installdir, stat.S_IWOTH, add=False)

    def sanity_check_step(self):
        """Custom sanity check for ANSYS."""
        
        ver = 'v%s' % ''.join(self.version.split('.'))

        custom_paths = {
                        'files': ["%s/fluent/bin/fluent%s" % (ver, x) for x in ['', '_arch', '_sysinfo']],
                        'dirs': ["%s/%s" % (ver,x) for x in ["ansys", "aisol", "CFD-Post","CFX"]]
                       }

        super(EB_ANSYS, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom extra module file entries for ANSYS."""
        
        guesses = super(EB_ANSYS, self).make_module_req_guess()

        ver = "v%s" % ''.join(self.version.split('.'))
        
        guesses.update({
                        "PATH": [os.path.join(ver, "tgrid", "bin") ,
                        os.path.join(ver, "Framework", "bin/linux64") ,
                        os.path.join(ver, "aisol", "bin/linux64"),
                        os.path.join(ver, "RSM", "bin"),
                        os.path.join(ver, "ansys", "bin"),
                        os.path.join(ver, "autodin", "bin"),
                        os.path.join(ver, "CFX", "bin"),
                        os.path.join(ver, "fluent", "bin"),
                        os.path.join(ver, "CFD-Post", "bin"),
                        os.path.join(ver, "TurboGrid", "bin"),
                        os.path.join(ver, "polyflow", "bin"),
                        os.path.join(ver, "IcePack", "bin")],
                       })
        return guesses
