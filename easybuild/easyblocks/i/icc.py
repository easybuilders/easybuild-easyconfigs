# #
# Copyright 2009-2015 Ghent University
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
from easybuild.tools.run import run_cmd


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

        if LooseVersion(self.version) >= LooseVersion('2016'):
            cfg_extras_map = {
                'COMPONENTS': 'ALL',
            }
        super(EB_icc, self).install_step(silent_cfg_names_map=silent_cfg_names_map, silent_cfg_extras=cfg_extras_map)

    def sanity_check_step(self):
        """Custom sanity check paths for icc."""

        binprefix = "bin/intel64"
        libprefix = "lib/intel64"
        if LooseVersion(self.version) >= LooseVersion("2011"):
            if LooseVersion(self.version) <= LooseVersion("2011.3.174"):
                binprefix = "bin"
            elif LooseVersion(self.version) >= LooseVersion("2013_sp1") and LooseVersion(self.version) < LooseVersion("2016"):
                binprefix = "bin"
                libprefix = "lib/intel64"
            elif LooseVersion(self.version) >= LooseVersion("2016"):
                binprefix = "bin"
                libprefix = "lib/intel64_lin"
            else:
                libprefix = "compiler/lib/intel64"

        binfiles = ["icc", "icpc"]
        if LooseVersion(self.version) < LooseVersion("2014"):
            binfiles += ["idb"]

        custom_paths = {
            'files': ["%s/%s" % (binprefix, x) for x in binfiles] +
                     ["%s/lib%s" % (libprefix, x) for x in ["iomp5.a", "iomp5.so"]],
            'dirs': [],
        }

        super(EB_icc, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Customize paths to check and add in environment.
        """
        # New Directory Layout for Intel Parallel Studio XE 2016
        # https://software.intel.com/en-us/articles/new-directory-layout-for-intel-parallel-studio-xe-2016
        debuggerpath = 'debugger_%s' % self.version.split('.')[0]
        if self.cfg['m32']:
            # 32-bit toolchain
            libpaths = ['lib', 'lib/ia32'],
            dirmap = {
                'PATH': ['bin', 'bin/ia32', 'tbb/bin/ia32'],
                'LD_LIBRARY_PATH': libpaths,
                'LIBRARY_PATH': libpaths,
                'MANPATH': ['man', 'share/man', 'man/en_US'],
                'IDB_HOME': ['bin/intel64']
            }
        else:
            if LooseVersion(self.version) < LooseVersion("2016"):
                # 64-bit toolkit
                libpaths = ['compiler/lib/intel64', 'lib/intel64', 'debugger/ipt/intel64/lib', 'ipp/lib/intel64', 'tbb/lib/intel64']
                dirmap = {
                    'PATH': ['bin/intel64', 'tbb/bin/intel64', 'ipp/bin/intel64', 'debugger/gdb/intel64/bin'],
                    'LD_LIBRARY_PATH': libpaths, 
                    'LIBRARY_PATH': libpaths,
                    'MANPATH': ['man', 'share/man', 'man/en_US', 'debugger/gdb/intel64/share/man'],
                    'CPATH': ['ipp/include', 'tbb/include'],
                    'INTEL_PYTHONHOME': ['debugger/python/intel64']
                }
            else:
                # 64-bit toolkit
                libpaths = ['daal/../compiler/lib/intel64_lin', 'daal/../tbb/lib/intel64_lin/gcc4.4', 'daal/lib/intel64_lin', '%s/libipt/intel64/lib' % debuggerpath,'tbb/lib/intel64/gcc4.4', 'mkl/lib/intel64', 'ipp/lib/intel64', 'ipp/../compiler/lib/intel64', 'compiler/lib/intel64']
                dirmap = {
                    'PATH': ['mpi/intel64/bin', 'ipp/bin/intel64', '%s/gdb/intel64/bin' % debuggerpath, 'bin/intel64'],
                    'LD_LIBRARY_PATH': libpaths,
                    'LIBRARY_PATH': libpaths,
                    'MANPATH': ['man/common', 'man/en_US', 'debugger/gdb/intel64/share/man'],
                    'CPATH': ['daal/include', 'tbb/include', 'mkl/include', 'ipp/include'],
                    'INTEL_PYTHONHOME': ['%s/python/intel64' % debuggerpath],
                    'DAALROOT': ['daal'],
#                    'MKLROOT': ['mkl'],
                    'TBBROOT': ['tbb'],
                    'IPPROOT': ['ipp'],
                    'CLASSPATH': ['daal/lib/daal.jar'],
                }


        # in recent Intel compiler distributions, the actual binaries are
        # in deeper directories, and symlinked in top-level directories
        # however, not all binaries are symlinked (e.g. mcpcom is not)
        # more recent versions of the Intel Compiler (2013.sp1 and newer)
        if os.path.isdir("%s/composer_xe_%s" % (self.installdir, self.version)):
            prefix = "composer_xe_%s" % self.version
            oldmap = dirmap
            dirmap = {}
            for k, vs in oldmap.items():
                dirmap[k] = []
                prefix = "composer_xe_%s" % self.version
                for v in vs:
                    v2 = "%s/%s" % (prefix, v)
                    if os.path.isdir("%s/%s" % (self.installdir, v2)):
                        dirmap[k].append(v2)

        if os.path.isdir("%s/compilers_and_libraries_%s/linux" % (self.installdir, self.version)):
            prefix = "compilers_and_libraries_%s/linux" % self.version
            oldmap = dirmap
            dirmap = {}
            for k, vs in oldmap.items():
                dirmap[k] = []
                for v in vs:
                    v2 = "%s/%s" % (prefix, v)
                    if os.path.exists("%s/%s" % (self.installdir, v2)):
                        dirmap[k].append(v2)

        return dirmap

    def make_module_extra(self):
        """Add extra environment variables for icc, for license file and NLS path."""
        txt = super(EB_icc, self).make_module_extra()
        txt += self.module_generator.prepend_paths(self.license_env_var, self.cfg['license_file'], allow_abs=True)
        txt += self.module_generator.prepend_paths('NLSPATH', '$root/idb/intel64/locale/%l_%t/%N')
        return txt

