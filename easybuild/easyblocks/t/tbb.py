##
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
##
"""
EasyBuild support for installing the Intel Threading Building Blocks (TBB) library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import glob
import os
import shutil
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_version
from easybuild.tools.systemtools import get_gcc_version


def get_tbb_gccprefix():
    """
    Find the correct gcc version for the lib dir of TBB
    """
    # using get_software_version('GCC') won't work, while the compiler toolchain is dummy:dummy, which does not
    # load dependencies.
    gccversion = get_software_version('GCC')
    # manual approach to at least have the system version of gcc
    if not gccversion:
        gccversion = get_gcc_version()

    # TBB directory structure
    # https://www.threadingbuildingblocks.org/docs/help/tbb_userguide/Linux_OS.htm
    tbbgccversion = 'gcc4.4'  # gcc version 4.4 or higher that may or may not support exception_ptr
    if gccversion and LooseVersion(gccversion) >= LooseVersion("4.1") and LooseVersion(gccversion) < LooseVersion("4.4"):
        tbbgccversion = 'gcc4.1'  # gcc version number between 4.1 and 4.4 that do not support exception_ptr

    return tbbgccversion


class EB_tbb(IntelBase):
    """EasyBlock for tbb, threading building blocks"""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for tbb"""
        super(EB_tbb, self).__init__(*args, **kwargs)
        self.libpath = 'UNKNOWN'

    def install_step(self):
        """Custom install step, to add extra symlinks"""
        silent_cfg_names_map = None

        if LooseVersion(self.version) < LooseVersion('4.2'):
            silent_cfg_names_map = {
                'activation_name': ACTIVATION_NAME_2012,
                'license_file_name': LICENSE_FILE_NAME_2012,
            }

        super(EB_tbb, self).install_step(silent_cfg_names_map=silent_cfg_names_map)

        # save libdir
        os.chdir(self.installdir)
        if LooseVersion(self.version) < LooseVersion('4.1.0'):
            libglob = 'tbb/lib/intel64/cc*libc*_kernel*'
        else:
            libglob = 'tbb/lib/intel64/gcc*'
        libs = sorted(glob.glob(libglob), key=LooseVersion)
        if len(libs):
            libdir = libs[-1]  # take the last one, should be ordered by cc get_version.
            # we're only interested in the last bit
            libdir = libdir.split('/')[-1]
        else:
            raise EasyBuildError("No libs found using %s in %s", libglob, self.installdir)
        self.libdir = libdir

        self.libpath = os.path.join('tbb', 'libs', 'intel64', libdir)
        self.log.debug("self.libpath: %s" % self.libpath)
        # applications go looking into tbb/lib so we move what's in there to libs
        # and symlink the right lib from /tbb/libs/intel64/... to lib
        install_libpath = os.path.join(self.installdir, 'tbb', 'lib')
        shutil.move(install_libpath, os.path.join(self.installdir, 'tbb', 'libs'))
        os.symlink(os.path.join(self.installdir, self.libpath), install_libpath)

    def sanity_check_step(self):
        custom_paths = {
            'files': [],
            'dirs': ['tbb/bin', 'tbb/lib', 'tbb/libs'],
        }
        super(EB_tbb, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add correct path to lib to LD_LIBRARY_PATH. and intel license file"""
        txt = super(EB_tbb, self).make_module_extra()
        txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', [self.libpath])
        txt += self.module_generator.prepend_paths('LIBRARY_PATH', [self.libpath])
        txt += self.module_generator.prepend_paths('CPATH', [os.path.join('tbb', 'include')])
        txt += self.module_generator.set_environment('TBBROOT', os.path.join(self.installdir, 'tbb'))
        return txt
