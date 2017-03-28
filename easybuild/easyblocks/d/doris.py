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
EasyBuild support for building and installing Doris, implemented as an easyblock

author: Kenneth Hoste (HPC-UGent)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import change_dir, mkdir
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd_qa


class EB_Doris(ConfigureMake):
    """Support for building/installing Doris."""

    def configure_step(self):
        """Custom configuration procedure for Doris."""
        fftw = get_software_root('FFTW')
        if fftw is None:
            raise EasyBuildError("Required dependency FFTW is missing")

        # create installation directory (and /bin subdirectory) early, make sure it doesn't get removed later
        self.make_installdir()
        mkdir(os.path.join(self.installdir, 'bin'))
        self.cfg["keeppreviousinstall"] = True

        # configure/build/install should be done from 'src' subdirectory
        change_dir('src')

        qa = {
            "===> Press enter to continue.": '',
            "===> What is your C++ compiler? [g++]": os.getenv('CXX'),
            "===> Do you have the FFTW library (y/n)? [n]": 'y',
            "===> What is the path to the FFTW library (libfftw3f.a or libfftw3f.so)? []": os.path.join(fftw, 'lib'),
            "===> What is the path to the FFTW include file (fftw3.h)? []": os.path.join(fftw, 'include'),
            "===> Do you have the VECLIB library (y/n)? [n]": 'n',
            "===> Do you have the LAPACK library (y/n)? [n]": 'y',
            "===> What is the path to the LAPACK library liblapack.a? []": os.getenv('LAPACK_LIB_DIR'),
            "===> Are you working on a Little Endian (X86 PC, Intel) machine (y/n)? [y]": 'y',
            "===> Installation of Doris in directory: /usr/local/bin (y/n)? [y]": 'n',
            "===> Enter installation directory (use absolute path):": os.path.join(self.installdir, 'bin'),
            "===> Press enter to continue (CTRL-C to exit).": '',
        }
        std_qa = {
            "===> Do you want to compile a more verbose DEBUG version \(y/n\)\? \[n\](.|\n)*expected results\)": 'n',
        }

        run_cmd_qa('./configure', qa, std_qa=std_qa, log_all=True, simple=True)

        # override some of the settings via options to 'make'
        lflags = "-L%s -lfftw3 " % os.path.join(fftw, 'lib')
        lflags += "-L%s %s" % (os.getenv('LAPACK_LIB_DIR'), os.getenv('LIBLAPACK_MT'))
        self.cfg.update('buildopts', 'LFLAGS="%s"' % lflags)

        self.cfg.update('buildopts', 'CFLAGSOPT="%s \$(DEFS)"' % os.getenv('CXXFLAGS'))

    def sanity_check_step(self):
        """Custom sanity check for Doris."""
        custom_paths = {
            'files': ['bin/cpx2ps', 'bin/doris', 'bin/plotcpm', 'bin/run'],
            'dirs': [],
        }
        super(EB_Doris, self).sanity_check_step(custom_paths=custom_paths)
