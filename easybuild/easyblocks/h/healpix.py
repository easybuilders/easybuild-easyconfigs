##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for building and installing HEALPix, implemented as an easyblock

@author: Kenneth Hoste (HPC-UGent)
"""
import os
import re

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd, run_cmd_qa
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_HEALPix(ConfigureMake):
    """Support for building/installing HEALPix."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for HEALPix."""
        super(EB_HEALPix, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def extract_step(self):
        """Extract sources."""
        # strip off 'Healpix_<version>' part to avoid having everything in a subdirectory
        self.cfg['unpack_options'] = "--strip-components=1"
        super(EB_HEALPix, self).extract_step()

    def configure_step(self):
        """Custom configuration procedure for HEALPix."""

        cfitsio = get_software_root('CFITSIO')
        if not cfitsio:
            raise EasyBuildError("Failed to determine root for CFITSIO, module not loaded?")

        self.comp_fam = self.toolchain.comp_family()
        if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
            cxx_config = '4'  # linux_icc
        elif self.comp_fam == toolchain.GCC:  #@UndefinedVariable
            cxx_config = '2'  # generic_gcc
        else:
            raise EasyBuildError("Don't know how which C++ configuration for the used toolchain.")

        cmd = "./configure -L"
        qa = {
            "Should I attempt to create these directories (Y\|n)?": 'Y',
            "full name of cfitsio library (libcfitsio.a):": '',
            "Do you want this modification to be done (y\|N)?": 'y',
            "enter suffix for directories ():": '',
            # configure for C (2), Fortran (3), C++ (4), then exit (0)
            "Enter your choice (configuration of packages can be done in any order):": ['2', '3', '4', '0'],
        }
        std_qa = {
            r"C compiler you want to use \(\S*\):": os.environ['CC'],
            r"enter name of your F90 compiler \(\S*\):": os.environ['F90'],
            r"enter name of your C compiler \(\S*\):": os.environ['CC'],
            r"options for C compiler \([^)]*\):": os.environ['CFLAGS'],
            r"enter compilation/optimisation flags for C compiler \([^)]*\):": os.environ['CFLAGS'],
            r"compilation flags for %s compiler \([^:]*\):" % os.environ['F90']: '',
            r"enter optimisation flags for %s compiler \([^)]*\):" % os.environ['F90']: os.environ['F90FLAGS'],
            r"location of cfitsio library \(\S*\):": os.path.join(cfitsio, 'lib'),
            r"cfitsio header fitsio.h \(\S*\):": os.path.join(cfitsio, 'include'),
            r"enter command for library archiving \([^)]*\):": '',
            r"archive creation \(and indexing\) command \([^)]*\):": '',
            r"A static library is produced by default. Do you also want a shared library.*": 'y',
            r"Available configurations for C\+\+ compilation are:[\s\n\S]*Choose one number:": cxx_config,
            r"PGPLOT.[\s\n]*Do you want to enable this option \?[\s\n]*\([^)]*\) \(y\|N\)": 'N',
            r"the parallel implementation[\s\n]*Enter choice.*": '1',
        }
        run_cmd_qa(cmd, qa, std_qa=std_qa, log_all=True, simple=True, log_ok=True)

    def build_step(self):
        """Custom build procedure for HEALPix."""
        # disable parallel build
        self.cfg['parallel'] = '1'
        self.log.debug("Disabled parallel build")
        super(EB_HEALPix, self).build_step()

    def install_step(self):
        """No dedicated install procedure for HEALPix."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for HEALPix."""

        custom_paths = {
            'files': [os.path.join('bin', x) for x in ['alteralm', 'anafast', 'hotspot', 'map2gif',
                                                       'median_filter', 'plmgen', 'sky_ng_sim',
                                                       'sky_ng_sim_bin', 'smoothing', 'synfast', 'ud_grade']] +
                     [os.path.join('lib', 'lib%s.a' % x) for x in ['chealpix', 'gif', 'healpix', 'hpxgif',
                                                                   'psht_healpix_f']] +
                     [os.path.join('lib', 'libchealpix.%s' % get_shared_lib_ext())],
            'dirs': [os.path.join('include')],
        }
        super(EB_HEALPix, self).sanity_check_step(custom_paths=custom_paths)
