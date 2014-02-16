# #
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
# #
"""
EasyBuild support for install the Intel C/C++ compiler suite, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import re
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.tools.filetools import run_cmd


def get_icc_version():
    """Obtain icc version string via 'icc --version'."""
    cmd = "icc --version"
    (out, _) = run_cmd(cmd, log_all=True, simple=False)

    ver_re = re.compile("^icc \(ICC\) (?P<version>[0-9.]+) [0-9]+$", re.M)
    version = ver_re.search(out).group('version')

    return version


class EB_icc(IntelBase):
    """Support for installing icc

    - tested with 11.1.046
        - will fail for all older versions (due to newer silent installer)
    """

    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """
        silent_cfg_names_map = None

        if LooseVersion(self.version) < LooseVersion('2013_sp1'):
            # since icc v2013_sp1, silent.cfg has been slightly changed to be 'more standard'

            silent_cfg_names_map = {
                'activation_name': ACTIVATION_NAME_2012,
                'license_file_name': LICENSE_FILE_NAME_2012,
            }

        super(EB_icc, self).install_step(silent_cfg_names_map=silent_cfg_names_map)

    def sanity_check_step(self):
        """Custom sanity check paths for icc."""

        binprefix = "bin/intel64"
        libprefix = "lib/intel64/lib"
        if LooseVersion(self.version) >= LooseVersion("2011"):
            if LooseVersion(self.version) <= LooseVersion("2011.3.174"):
                binprefix = "bin"
            elif LooseVersion(self.version) >= LooseVersion("2013_sp1"):
                binprefix = "bin"
                libprefix = "lib/intel64/lib"
            else:
                libprefix = "compiler/lib/intel64/lib"

        custom_paths = {
            'files': ["%s/%s" % (binprefix, x) for x in ["icc", "icpc", "idb"]] +
                     ["%s%s" % (libprefix, x) for x in ["iomp5.a", "iomp5.so"]],
            'dirs': [],
        }

        super(EB_icc, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Customize paths to check and add in environment.
        """
        if self.cfg['m32']:
            # 32-bit toolchain
            dirmap = {
                'PATH': ['bin', 'bin/ia32', 'tbb/bin/ia32'],
                'LD_LIBRARY_PATH': ['lib', 'lib/ia32'],
                'LIBRARY_PATH': ['lib', 'lib/ia32'],
                'MANPATH': ['man', 'share/man', 'man/en_US'],
                'IDB_HOME': ['bin/intel64']
            }
        else:
            # 64-bit toolit
            dirmap = {
                'PATH': ['bin', 'bin/intel64', 'tbb/bin/emt64'],
                'LD_LIBRARY_PATH': ['lib', 'lib/intel64'],
                'LIBRARY_PATH': ['lib', 'lib/intel64'],
                'MANPATH': ['man', 'share/man', 'man/en_US'],
                'IDB_HOME': ['bin/intel64']
            }

        # in recent Intel compiler distributions, the actual binaries are
        # in deeper directories, and symlinked in top-level directories
        # however, not all binaries are symlinked (e.g. mcpcom is not)
        if os.path.isdir("%s/composerxe-%s" % (self.installdir, self.version)):
            prefix = "composerxe-%s" % self.version
            oldmap = dirmap
            dirmap = {}
            for k, vs in oldmap.items():
                dirmap[k] = []
                if k == "LD_LIBRARY_PATH":
                    prefix = "composerxe-%s/compiler" % self.version
                else:
                    prefix = "composerxe-%s" % self.version
                for v in vs:
                    v2 = "%s/%s" % (prefix, v)
                    dirmap[k].append(v2)

        elif os.path.isdir("%s/compiler" % (self.installdir)):
            prefix = "compiler"
            oldmap = dirmap
            dirmap = {}
            for k, vs in oldmap.items():
                dirmap[k] = []
                prefix = ''
                if k == "LD_LIBRARY_PATH":
                    prefix = "compiler/"
                for v in vs:
                    v2 = "%s%s" % (prefix, v)
                    dirmap[k].append(v2)

        return dirmap

    def make_module_extra(self):
        """Add extra environment variables for icc, for license file and NLS path."""

        txt = super(EB_icc, self).make_module_extra()

        txt += "prepend-path\t%s\t\t%s\n" % (self.license_env_var, self.license_file)
        txt += "prepend-path\t%s\t\t$root/%s\n" % ('NLSPATH', 'idb/intel64/locale/%l_%t/%N')

        return txt
