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
EasyBuild support for installing FLUENT, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import stat
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import adjust_permissions
from easybuild.tools.run import run_cmd


class EB_FLUENT(EasyBlock):
    """Support for installing FLUENT."""

    def __init__(self, *args, **kwargs):
        """Custom constructor for FLUENT easyblock, initialize/define class parameters."""
        super(EB_FLUENT, self).__init__(*args, **kwargs)
        self.fluent_verdir = 'v%s' % ''.join(self.version.split('.')[:2])

    def configure_step(self):
        """No configuration for FLUENT."""
        pass

    def build_step(self):
        """No building for FLUENT."""
        pass

    def install_step(self):
        """Custom install procedure for FLUENT."""

        extra_args =''
        # only include -noroot flag for older versions
        if LooseVersion(self.version) < LooseVersion('15.0'):
            extra_args += '-noroot'

        cmd = "./INSTALL %s -debug -silent -install_dir %s %s" % (extra_args, self.installdir, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        adjust_permissions(self.installdir, stat.S_IWOTH, add=False)

    def sanity_check_step(self):
        """Custom sanity check for FLUENT."""
        custom_paths = {
            'files': ["%s/fluent/bin/fluent%s" % (self.fluent_verdir, x) for x in ['', '_arch', '_sysinfo']],
            'dirs': ["%s/%s" % (self.fluent_verdir, x) for x in ["ansys", "aisol", "CFD-Post"]]
        }
        super(EB_FLUENT, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom extra module file entries for FLUENT."""
        guesses = super(EB_FLUENT, self).make_module_req_guess()

        guesses.update({
            "PATH": [os.path.join(self.fluent_verdir, "fluent", "bin")],
            "LD_LIBRARY_PATH": [os.path.join(self.fluent_verdir, "fluent", "lib")],
        })

        return guesses
