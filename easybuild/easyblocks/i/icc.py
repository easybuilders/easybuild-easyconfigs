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
from easybuild.tools.modules import get_software_root, get_software_version
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

        cfg_extras_map = {}
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
            elif LooseVersion(self.version) >= LooseVersion("2013_sp1"):
                binprefix = "bin"
                if LooseVersion(self.version) >= LooseVersion("2016"):
                    libprefix = "lib/intel64_lin"
            else:
                libprefix = "compiler/lib/intel64"

        binfiles = ["icc", "icpc"]
        if LooseVersion(self.version) < LooseVersion("2014"):
            binfiles += ["idb"]

        custom_paths = {
            'files': [os.path.join(binprefix, x) for x in binfiles] +
                     [os.path.join(libprefix, 'lib%s' % x) for x in ['iomp5.a', 'iomp5.so']],
            'dirs': [],
        }

        super(EB_icc, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Customize paths to check and add in environment.
        """
        debuggerpath = None
        prefix = None
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
            # 64-bit toolkit
            
            # using get_software_version('GCC') won't work, while the compiler toolchain is dummy:dummy, which does not
            # load dependencies. 
            gccversion = get_software_version('GCC')
            # manual approach to at least have the system version of gcc
            if not gccversion:
                cmd = 'gcc --version'
                (out, _) = run_cmd(cmd, log_all=True, simple=False)
                ver_re = re.compile("^gcc \(GCC\) (?P<version>[0-9.]+) [0-9]+", re.M)
                gccversion = ver_re.search(out).group('version')

            # TBB directory structure
            # https://www.threadingbuildingblocks.org/docs/help/tbb_userguide/Linux_OS.htm
            tbbgccversion = 'gcc4.4' # gcc version 4.4 or higher that may or may not support exception_ptr
            if gccversion and LooseVersion(gccversion) >= LooseVersion("4.1") and LooseVersion(gccversion) < LooseVersion("4.4"):
                tbbgccversion = 'gcc4.1' # gcc version number between 4.1 and 4.4 that do not support exception_ptr

            if LooseVersion(self.version) < LooseVersion("2016"):
                prefix = "composer_xe_%s" % self.version

                # Debugger is dependent on INTEL_PYTHONHOME since version 2015 and newer
                if LooseVersion(self.version) >= LooseVersion("2015"):
                    # Debugger requires INTEL_PYTHONHOME, which only allows for a single value
                    debuggerpath = os.path.join('composer_xe_%s' % self.version.split('.')[0], 'debugger')

                libpaths = [os.path.join('tbb/lib/intel64', tbbgccversion),
                            'ipp/lib/intel64',
                            'debugger/ipt/intel64/lib',
                            'lib/intel64',
                            'compiler/lib/intel64',
                           ]
                dirmap = {
                    'PATH': ['debugger/gdb/intel64/bin', 'ipp/bin/intel64', 'tbb/bin/intel64', 'bin/intel64'],
                    'LD_LIBRARY_PATH': libpaths, 
                    'LIBRARY_PATH': libpaths,
                    'MANPATH': ['debugger/gdb/intel64/share/man', 'man/en_US', 'share/man', 'man'],
                    'CPATH': ['ipp/include', 'tbb/include'],
                }
            else:
                # New Directory Layout for Intel Parallel Studio XE 2016
                # https://software.intel.com/en-us/articles/new-directory-layout-for-intel-parallel-studio-xe-2016
                prefix = "compilers_and_libraries_%s/linux" % self.version
                # Debugger requires INTEL_PYTHONHOME, which only allows for a single value
                debuggerpath = 'debugger_%s' % self.version.split('.')[0]

                libpaths = ['daal/../compiler/lib/intel64_lin',
                            os.path.join('daal/../tbb/lib/intel64_lin', tbbgccversion),
                            'daal/lib/intel64_lin',
                            os.path.join(debuggerpath, 'libipt/intel64/lib'),
                            os.path.join('tbb/lib/intel64', tbbgccversion),
                            'mkl/lib/intel64',
                            'ipp/lib/intel64',
                            'ipp/../compiler/lib/intel64',
                            'mpi/intel64',
                            'compiler/lib/intel64',
                            'lib/intel64_lin',
                           ]
                dirmap = {
                    'PATH': ['mpi/intel64/bin',
                             'ipp/bin/intel64',
                              os.path.join(debuggerpath, 'gdb/intel64/bin'),
                             'bin/intel64',
                             'bin',
                            ],
                    'LD_LIBRARY_PATH': libpaths,
                    'LIBRARY_PATH': libpaths,
                    'MANPATH': ['man/common', 'man/en_US', 'debugger/gdb/intel64/share/man'],
                    'CPATH': ['ipp/include', 'mkl/include', 'tbb/include', 'daal/include'],
                    'DAALROOT': ['daal'],
                    'TBBROOT': ['tbb'],
                    'IPPROOT': ['ipp'],
                    'CLASSPATH': ['daal/lib/daal.jar']
                }

        # set debugger path
        if debuggerpath:
            if os.path.isdir(os.path.join(self.installdir, debuggerpath, 'python/intel64')):
                self.cfg['modextravars'] = { 'INTEL_PYTHONHOME': os.path.join('$root', debuggerpath, 'python/intel64') }

        # in recent Intel compiler distributions, the actual binaries are
        # in deeper directories, and symlinked in top-level directories
        # however, not all binaries are symlinked (e.g. mcpcom is not)
        # more recent versions of the Intel Compiler (2013.sp1 and newer)
        if os.path.isdir(os.path.join(self.installdir, prefix)):
            oldmap = dirmap
            dirmap = {}
            for k, vs in oldmap.items():
                dirmap[k] = []
                for v in vs:
                    v2 = os.path.join(prefix, v)
                    if os.path.exists(os.path.join(self.installdir, v2)):
                        dirmap[k].append(v2)
                    elif os.path.isdir(os.path.join(self.installdir, v)):
                        dirmap[k].append(v)

        return dirmap

