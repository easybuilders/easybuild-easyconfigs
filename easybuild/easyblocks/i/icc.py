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
@author: Ward Poelmans (Ghent University)
"""

import os
import re
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.easyblocks.t.tbb import get_tbb_gccprefix
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

    def configure_step(self):
        """have fallback for components for > 2016 versions"""

        if LooseVersion(self.version) >= LooseVersion('2016') and not self.cfg['components']:
            self.log.warning("No components specified")

        super(EB_icc, self).configure_step()

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
        libprefix = "lib/intel64"
        if LooseVersion(self.version) >= LooseVersion("2011"):
            if LooseVersion(self.version) <= LooseVersion("2011.3.174"):
                binprefix = "bin"
            elif LooseVersion(self.version) >= LooseVersion("2013_sp1"):
                binprefix = "bin"
            else:
                libprefix = "compiler/lib/intel64"

        binfiles = ["icc", "icpc"]
        if LooseVersion(self.version) < LooseVersion("2014"):
            binfiles += ["idb"]

        custom_paths = {
            'files': [os.path.join(binprefix, x) for x in binfiles] +
            [os.path.join(libprefix, 'lib%s' % x) for x in ['iomp5.a', 'iomp5.so']] +
            ['include/omp.h'],
            'dirs': [],
        }

        super(EB_icc, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Customize paths to check and add in environment.
        """
        self.debuggerpath = None
        prefix = None
        tbbgccversion = get_tbb_gccprefix()

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
            dirmap = {
                'PATH': [
                    'mpi/intel64/bin',
                    'ipp/bin/intel64',
                    'tbb/bin/intel64',
                    'bin/intel64',
                    'bin',
                ],
                # in the end we set 'LIBRARY_PATH' equal to 'LD_LIBRARY_PATH'
                'LD_LIBRARY_PATH': [
                    os.path.join('tbb', 'lib', 'intel64', tbbgccversion),
                    'debugger/ipt/intel64/lib',
                    'lib/intel64',
                    'compiler/lib/intel64',
                    'mkl/lib/intel64',
                    'ipp/lib/intel64',
                    'mpi/intel64',
                    'compiler/lib/intel64',
                ],
                'MANPATH': ['man/common', 'man/en_US', 'debugger/gdb/intel64/share/man'],
                'CPATH': ['include', 'ipp/include', 'mkl/include', 'tbb/include', 'daal/include'],
                'DAALROOT': ['daal'],
                'TBBROOT': ['tbb'],
                'IPPROOT': ['ipp'],
                'CLASSPATH': ['daal/lib/daal.jar']
            }

            if LooseVersion(self.version) < LooseVersion("2016"):
                prefix = "composer_xe_%s" % self.version

                # Debugger is dependent on INTEL_PYTHONHOME since version 2015 and newer
                if LooseVersion(self.version) >= LooseVersion("2015"):
                    # Debugger requires INTEL_PYTHONHOME, which only allows for a single value
                    self.debuggerpath = os.path.join('composer_xe_%s' % self.version.split('.')[0], 'debugger')

                dirmap['PATH'].append('debugger/gdb/intel64/bin')
                dirmap['MANPATH'].extend(['debugger/gdb/intel64/share/man', 'share/man', 'man'])
            else:
                # New Directory Layout for Intel Parallel Studio XE 2016
                # https://software.intel.com/en-us/articles/new-directory-layout-for-intel-parallel-studio-xe-2016
                prefix = "compilers_and_libraries_%s/linux" % self.version
                # Debugger requires INTEL_PYTHONHOME, which only allows for a single value
                self.debuggerpath = 'debugger_%s' % self.version.split('.')[0]

                libpaths = [
                    os.path.join(self.debuggerpath, 'libipt/intel64/lib'),
                    'daal/lib/intel64_lin',
                ]

                dirmap['LD_LIBRARY_PATH'].extend(libpaths)

        dirmap['LIBRARY_PATH'] = dirmap['LD_LIBRARY_PATH']

        # set debugger path
        if self.debuggerpath:
            dirmap['PATH'].append(os.path.join(self.debuggerpath, 'gdb', 'intel64', 'bin'))

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

    def make_module_extra(self):
        """Custom variables for OpenBabel module."""
        txt = super(EB_icc, self).make_module_extra()
        intel_pythonhome = os.path.join('$root', self.debuggerpath, 'python', 'intel64')
        txt += self.module_generator.set_environment('INTEL_PYTHONHOME', intel_pythonhome)
        return txt
