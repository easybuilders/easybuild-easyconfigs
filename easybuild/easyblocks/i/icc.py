# #
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
# #
"""
EasyBuild support for install the Intel C/C++ compiler suite, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Ward Poelmans (Ghent University)
@author: Fokko Masselink
"""

import os
import re
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, COMP_ALL
from easybuild.easyblocks.generic.intelbase import LICENSE_FILE_NAME_2012
from easybuild.easyblocks.t.tbb import get_tbb_gccprefix
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


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

    def __init__(self, *args, **kwargs):
        """Constructor, initialize class variables."""
        super(EB_icc, self).__init__(*args, **kwargs)

        self.debuggerpath = None

        if LooseVersion(self.version) >= LooseVersion('2016') and self.cfg['components'] is None:
            # we need to use 'ALL' by default, using 'DEFAULTS' results in key things not being installed (e.g. bin/icc)
            self.cfg['components'] = [COMP_ALL]
            self.log.debug("Nothing specified for components, but required for version 2016, using %s instead",
                           self.cfg['components'])

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

        binprefix = 'bin/intel64'
        libprefix = 'lib/intel64'
        if LooseVersion(self.version) >= LooseVersion('2011'):
            if LooseVersion(self.version) <= LooseVersion('2011.3.174'):
                binprefix = 'bin'
            elif LooseVersion(self.version) >= LooseVersion('2013_sp1'):
                binprefix = 'bin'
            else:
                libprefix = 'compiler/lib/intel64'

        binfiles = ['icc', 'icpc']
        if LooseVersion(self.version) < LooseVersion('2014'):
            binfiles += ['idb']

        binaries = [os.path.join(binprefix, f) for f in binfiles]
        libraries = [os.path.join(libprefix, 'lib%s' % l) for l in ['iomp5.a', 'iomp5.%s' % get_shared_lib_ext()]]
        sanity_check_files = binaries + libraries
        if LooseVersion(self.version) > LooseVersion('2015'):
            sanity_check_files.append('include/omp.h')

        custom_paths = {
            'files': sanity_check_files,
            'dirs': [],
        }

        super(EB_icc, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        Additional paths to consider for prepend-paths statements in module file
        """
        prefix = None

        # guesses per environment variables
        # some of these paths only apply to certain versions, but that doesn't really matter
        # existence of paths is checked by module generator before 'prepend-paths' statements are included
        guesses = {
            'CLASSPATH': ['daal/lib/daal.jar'],
            # 'include' is deliberately omitted, including it causes problems, e.g. with complex.h and std::complex
            # cfr. https://software.intel.com/en-us/forums/intel-c-compiler/topic/338378
            'CPATH': ['daal/include', 'ipp/include', 'mkl/include', 'tbb/include'],
            'DAALROOT': ['daal'],
            'IDB_HOME': ['bin/intel64'],
            'IPPROOT': ['ipp'],
            'LD_LIBRARY_PATH': ['lib'],
            'LIBRARY_PATH': ['lib'],
            'MANPATH': ['debugger/gdb/intel64/share/man', 'man', 'man/common', 'man/en_US', 'share/man'],
            'PATH': ['bin'],
            'TBBROOT': ['tbb'],
        }

        if self.cfg['m32']:
            # 32-bit toolchain
            guesses['PATH'].extend(['bin/ia32', 'tbb/bin/ia32'])
            # in the end we set 'LIBRARY_PATH' equal to 'LD_LIBRARY_PATH'
            guesses['LD_LIBRARY_PATH'].append('lib/ia32')

        else:
            # 64-bit toolkit
            guesses['PATH'].extend([
                'bin/intel64',
                'debugger/gdb/intel64/bin',
                'ipp/bin/intel64',
                'mpi/intel64/bin',
                'tbb/bin/emt64',
                'tbb/bin/intel64',
            ])

            # in the end we set 'LIBRARY_PATH' equal to 'LD_LIBRARY_PATH'
            guesses['LD_LIBRARY_PATH'].extend([
                'compiler/lib/intel64',
                'debugger/ipt/intel64/lib',
                'ipp/lib/intel64',
                'mkl/lib/intel64',
                'mpi/intel64',
                'tbb/lib/intel64/%s' % get_tbb_gccprefix(),
            ])

            if LooseVersion(self.version) < LooseVersion('2016'):
                prefix = 'composer-xe-%s' % self.version

                # debugger is dependent on $INTEL_PYTHONHOME since version 2015 and newer
                if LooseVersion(self.version) >= LooseVersion('2015'):
                    self.debuggerpath = os.path.join('composer-xe-%s' % self.version.split('.')[0], 'debugger')

            else:
                # new directory layout for Intel Parallel Studio XE 2016
                # https://software.intel.com/en-us/articles/new-directory-layout-for-intel-parallel-studio-xe-2016
                prefix = 'compilers_and_libraries_%s/linux' % self.version
                # Debugger requires INTEL_PYTHONHOME, which only allows for a single value
                self.debuggerpath = 'debugger_%s' % self.version.split('.')[0]

                guesses['LD_LIBRARY_PATH'].extend([
                    os.path.join(self.debuggerpath, 'libipt/intel64/lib'),
                    'daal/lib/intel64_lin',
                ])

            # 'lib/intel64' is deliberately listed last, so it gets precedence over subdirs
            guesses['LD_LIBRARY_PATH'].append('lib/intel64')

        guesses['LIBRARY_PATH'] = guesses['LD_LIBRARY_PATH']

        # set debugger path
        if self.debuggerpath:
            guesses['PATH'].append(os.path.join(self.debuggerpath, 'gdb', 'intel64', 'bin'))

        # in recent Intel compiler distributions, the actual binaries are
        # in deeper directories, and symlinked in top-level directories
        # however, not all binaries are symlinked (e.g. mcpcom is not)
        if prefix and os.path.isdir(os.path.join(self.installdir, prefix)):
            for key, subdirs in guesses.items():
                guesses[key].extend([os.path.join(prefix, subdir) for subdir in subdirs])

        return guesses

    def make_module_extra(self):
        """Additional custom variables for icc: $INTEL_PYTHONHOME."""
        txt = super(EB_icc, self).make_module_extra()

        if self.debuggerpath:
            intel_pythonhome = os.path.join(self.installdir, self.debuggerpath, 'python', 'intel64')
            if os.path.isdir(intel_pythonhome):
                txt += self.module_generator.set_environment('INTEL_PYTHONHOME', intel_pythonhome)

        return txt
