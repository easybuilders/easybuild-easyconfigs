##
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
##
"""
EasyBuild support for building and installing Ferret, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: George Fanourgakis (The Cyprus Institute)
"""


import os,re,fileinput,sys
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd

class EB_Ferret(ConfigureMake):
    """Support for building/installing Ferret."""

    def configure_step(self):
        """Configure Ferret build."""

        buildtype = "x86_64-linux"

        try:
            os.chdir('FERRET')
        except OSError, err:
            raise EasyBuildError("Failed to change to FERRET dir: %s", err)

        deps = ['HDF5', 'netCDF', 'Java']

        for name in deps:
            if not get_software_root(name):
                raise EasyBuildError("%s module not loaded?", name)

        fn = "site_specific.mk"

        for line in fileinput.input(fn, inplace=1, backup='.orig'):

            line = re.sub(r"^BUILDTYPE\s*=.*", "BUILDTYPE = %s" % buildtype, line)
            line = re.sub(r"^INSTALL_FER_DIR =.*", "INSTALL_FER_DIR = %s" % self.installdir, line)

            for name in deps:
                line = re.sub(r"^(%s.*DIR\s*)=.*" % name.upper(), r"\1 = %s" % get_software_root(name), line)

            sys.stdout.write(line)

        comp_vars = {
            'CC':'CC',
            'CFLAGS':'CFLAGS',
            'CPPFLAGS':'CPPFLAGS',
            'FC':'F77',
        }

        fn = 'xgks/CUSTOMIZE.%s' % buildtype

        for line in fileinput.input(fn, inplace=1, backup='.orig'):

            for x,y in comp_vars.items():
                line = re.sub(r"^(%s\s*)=.*" % x, r"\1=%s" % os.getenv(y), line)

            line = re.sub(r"^(FFLAGS\s*=').*-m64 (.*)", r"\1%s \2" % os.getenv('FFLAGS'), line)
            line = re.sub(r"^(LD_X11\s*)=.*", r"\1='-L/usr/lib64/X11 -lX11'", line)

            sys.stdout.write(line)

        comp_vars = {
            'CC':'CC',
            'CXX':'CXX',
            'F77':'F77',
            'FC':'F77',
        }

        fns = [
            'fer/platform_specific_flags.mk.%s' % buildtype,
            'ppl/platform_specific_flags.mk.%s' % buildtype,
             'external_functions/ef_utility/platform_specific_flags.mk.%s' % buildtype,
        ]

        for fn in fns:
            for line in fileinput.input(fn, inplace=1, backup='.orig'):
                for x,y in comp_vars.items():
                    line = re.sub(r"^(\s*%s\s*)=.*" % x, r"\1 = %s" % os.getenv(y), line)

                if self.toolchain.comp_family() == toolchain.INTELCOMP:
                    line = re.sub(r"^(\s*LD\s*)=.*", r"\1 = %s -nofor-main" % os.getenv("F77"), line)
                    for x in ["CFLAGS", "FFLAGS"]:
                        line = re.sub(r"^(\s*%s\s*=\s*\$\(CPP_FLAGS\)).*\\" % x, r"\1 %s \\" % os.getenv(x), line)

                sys.stdout.write(line)

    def sanity_check_step(self):
        """Custom sanity check for Ferret."""

        custom_paths = {
                        'files': ["bin/ferret_v%s" % self.version],
                        'dirs': [],
                       }

        super(EB_Ferret, self).sanity_check_step(custom_paths=custom_paths)
