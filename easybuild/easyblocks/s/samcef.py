##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for building and installing Samcef, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import stat
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import adjust_permissions
from easybuild.tools.run import run_cmd_qa


class EB_Samcef(EasyBlock):
    """Support for building/installing Samcef."""

    def configure_step(self):
        """No configuration step for Samcef."""
        pass

    def build_step(self):
        """No build step for Samcef."""
        pass

    def install_step(self):
        """Custom install procedure for Samcef."""

        # e.g.: 17.0-03 => 17, 17.0, 170
        maj_ver = self.version.split('.')[0]
        main_ver = self.version.split('-')[0]
        flat_ver = ''.join(main_ver.split('.'))

        qa = {
            "Default language ? (E=English, F=French, default E): ": 'E',
            "Default Postscript printer ? (default: none): ": '',
            "Type RETURN to continue": '',
        }

        no_qa = []
        std_qa = {
            r"Installation for:.*[\s\n]*Continue \? \(y/n, default y\):": 'y',
            r" 1 Install Samcef %s \(%s\)[\s\n]*.*[\s\n]*Install type .*" % (maj_ver, main_ver): '1',
            r"Install SHORT INTEGERS VERSION \(i4\)[\s\na-zA-Z0-9().-]*Continue \? \(y/n, default y\):": 'n',
            r"Install LONG INTEGERS VERSION \(i8\)[\s\na-zA-Z0-9().-]*Continue \? \(y/n, default y\):": 'y',
            r"Pathname of install directory \(.*\):": self.installdir,
            r"Directory .* exists, use it \? \(y/n, default y\):": 'y',
            r"Installation directory\s*:.*[\s\n]*.*[\s\n]*Continue \? \(y/n, default:y\):": 'y',
            # option '2' is SAMCEF + object libraries
            r"Selection size: 0[\s\n]*Your selection:": '2',
            # 'i' for install after making a selection
            r"Selection size: [1-9][0-9]*[\s\n]*Your selection:": 'i',
            r"Prerequisite OK[\s\n]*Continue \? \(y/n, default y\):": 'y',
            r"Samcef users can modify these values.*[\s\n]*Continue \? \(y/n, default y\):": 'y',
            r"What is the hostname of your license server \( without  at sign @ \) \? ": 'localhost',
            r"Confirm .* as the LMS Samtech Licence server \? \(y/n, default n\): ": 'y',
            r"2 Floating RLM license[\s\n]*Type a value \(1/2, default 1 \)": '2',
        }

        # e.g., v170_inst.csh
        install_script = './v%s_inst.csh' % flat_ver

        # make sure script is executable (unpack with 7z doesn't preserve permissions)
        adjust_permissions(install_script, stat.S_IXUSR, add=True)

        run_cmd_qa(install_script, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for Samcef."""
        custom_paths = {
            'files': ['samcef'],
            'dirs': [],
        }
        super(EB_Samcef, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Include Samcef install directory in $PATH."""
        txt = super(EB_Samcef, self).make_module_extra()
        txt += self.module_generator.prepend_paths('PATH', [''])
        return txt
