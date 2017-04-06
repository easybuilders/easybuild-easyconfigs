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
        self.cfg['keeppreviousinstall'] = True

        # configure/build/install should be done from 'src' subdirectory
        change_dir(os.path.join(self.cfg['start_dir'], 'src'))

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

    def build_step(self):
        """Custom build procedure for Doris."""
        common_buildopts = self.cfg['buildopts']

        # build Doris
        change_dir(os.path.join(self.cfg['start_dir'], 'src'))

        # override some of the settings via options to 'make'
        lflags = "-L%s -lfftw3 " % os.path.join(get_software_root('FFTW'), 'lib')
        lflags += "-L%s %s" % (os.getenv('LAPACK_LIB_DIR'), os.getenv('LIBLAPACK_MT'))
        self.cfg.update('buildopts', 'LFLAGS="%s"' % lflags)
        self.cfg.update('buildopts', 'CFLAGSOPT="%s \$(DEFS)"' % os.getenv('CXXFLAGS'))

        super(EB_Doris, self).build_step()

        # build SARtools
        change_dir(os.path.join(self.cfg['start_dir'], 'SARtools'))

        self.cfg['buildopts'] = common_buildopts
        self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CXX'))
        cflags = os.getenv('CXXFLAGS') + " -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE"
        self.cfg.update('buildopts', 'CFLAGS="%s"' % cflags)

        super(EB_Doris, self).build_step()

        # build ENVISAT_TOOLS
        change_dir(os.path.join(self.cfg['start_dir'], 'ENVISAT_TOOLS'))

        self.cfg['buildopts'] = common_buildopts
        self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CC'))
        self.cfg.update('buildopts', 'CFLAGS="%s"' % os.getenv('CFLAGS'))

        super(EB_Doris, self).build_step()

    def install_step(self):
        """Custom build procedure for Doris."""
        # install Doris
        change_dir(os.path.join(self.cfg['start_dir'], 'src'))
        super(EB_Doris, self).install_step()

        # install SARtools
        self.cfg.update('installopts', 'INSTALL_DIR=%s' % os.path.join(self.installdir, 'bin'))
        change_dir(os.path.join(self.cfg['start_dir'], 'SARtools'))
        super(EB_Doris, self).install_step()

        # install ENVISAT_TOOLS
        change_dir(os.path.join(self.cfg['start_dir'], 'ENVISAT_TOOLS'))
        self.cfg.update('installopts', 'CC="%s"' % os.getenv('CC'))
        self.cfg.update('installopts', 'CFLAGS="%s"' % os.getenv('CFLAGS'))
        super(EB_Doris, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for Doris."""
        doris_bins = ['cpx2ps', 'doris', 'plotcpm', 'run']
        sartools_bins = ['bkconvert', 'cpxfiddle', 'flapjack', 'floatmult', 'wrap']
        envisat_tools_bins = ['envisat_dump_header', 'envisat_dump_data']
        custom_paths = {
            'files': [os.path.join('bin', x) for x in doris_bins + sartools_bins + envisat_tools_bins],
            'dirs': [],
        }
        super(EB_Doris, self).sanity_check_step(custom_paths=custom_paths)
