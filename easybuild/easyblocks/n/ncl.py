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
EasyBuild support for building and installing NCL, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import fileinput
import os
import re
import sys
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_NCL(EasyBlock):
    """Support for building/installing NCL."""

    def configure_step(self):
        """Configure build:
        - create Makefile.ini using make and run ymake script to create config file
        - patch config file with correct settings, and add missing config entries
        - create config/Site.local file to avoid interactive install
        - generate Makefile using config/ymkmf sciprt
        -
        """

        try:
            os.chdir('config')
        except OSError, err:
            raise EasyBuildError("Failed to change to the 'config' dir: %s", err)

        cmd = "make -f Makefile.ini"
        run_cmd(cmd, log_all=True, simple=True)

        cmd = "./ymake -config $PWD"
        run_cmd(cmd, log_all=True, simple=True)

        # figure out name of config file
        cfg_regexp = re.compile('^\s*SYSTEM_INCLUDE\s*=\s*"(.*)"\s*$', re.M)
        f = open("Makefile", "r")
        txt = f.read()
        f.close()
        cfg_filename = cfg_regexp.search(txt).group(1)

        # adjust config file as needed
        ctof_libs = ''
        ifort = get_software_root('ifort')
        if ifort:
            if LooseVersion(get_software_version('ifort')) < LooseVersion('2011.4'):
                ctof_libs = '-lm -L%s/lib/intel64 -lifcore -lifport' % ifort
            else:
                ctof_libs = '-lm -L%s/compiler/lib/intel64 -lifcore -lifport' % ifort
        elif get_software_root('GCC'):
            ctof_libs = '-lgfortran -lm'
        macrodict = {
                     'CCompiler': os.getenv('CC'),
                     'FCompiler': os.getenv('F90'),
                     'CcOptions': '-ansi %s' % os.getenv('CFLAGS'),
                     'FcOptions': os.getenv('FFLAGS'),
                     'COptimizeFlag': os.getenv('CFLAGS'),
                     'FOptimizeFlag': os.getenv('FFLAGS'),
                     'ExtraSysLibraries': os.getenv('LDFLAGS'),
                     'CtoFLibraries': ctof_libs
                    }

        # replace config entries that are already there
        for line in fileinput.input(cfg_filename, inplace=1, backup='%s.orig' % cfg_filename):
            for (key, val) in macrodict.items():
                regexp = re.compile("(#define %s\s*).*" % key)
                match = regexp.search(line)
                if match:
                    line = "#define %s %s\n" % (key, val)
                    macrodict.pop(key)
            sys.stdout.write(line)

        # add remaining config entries
        f = open(cfg_filename, "a")
        for (key, val) in macrodict.items():
            f.write("#define %s %s\n" % (key, val))
        f.close()

        f = open(cfg_filename, "r")
        self.log.debug("Contents of %s: %s" % (cfg_filename, f.read()))
        f.close()

        # configure
        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            raise EasyBuildError("Failed to change to the build dir %s: %s", self.cfg['start_dir'], err)

        # instead of running the Configure script that asks a zillion questions,
        # let's just generate the config/Site.local file ourselves...

        # order of deps is important
        # HDF needs to go after netCDF, because both have a netcdf.h include file
        deps = ["HDF5", "JasPer", "netCDF", "HDF", "g2lib", "g2clib", "Szip", "UDUNITS"]

        libs = ''
        includes = ''
        for dep in deps:
            root = get_software_root(dep)
            if not root:
                raise EasyBuildError("%s not available", dep)
            libs += ' -L%s/lib ' % root
            includes += ' -I%s/include ' % root

        opt_deps = ["netCDF-Fortran", "GDAL"]
        libs_map = {
                    'netCDF-Fortran': '-lnetcdff -lnetcdf',
                    'GDAL': '-lgdal',
                   }
        for dep in opt_deps:
            root = get_software_root(dep)
            if root:
                libs += ' -L%s/lib %s ' % (root, libs_map[dep])
                includes += ' -I%s/include ' % root

        cfgtxt="""#ifdef FirstSite
#endif /* FirstSite */

#ifdef SecondSite

#define YmakeRoot %(installdir)s

#define LibSearch %(libs)s
#define IncSearch %(includes)s

#define BuildNCL 1
#define HDFlib
#define HDFEOSlib
#define BuildGRIB2 1
#define BuildESMF 1

#define UdUnitslib -ludunits2

#define BuildRasterHDF 0
#define BuildHDF4 0
#define BuildTRIANGLE 0
#define BuildHDFEOS 0
#define BuildHDFEOS5 0

#endif /* SecondSite */
""" % {
       'installdir': self.installdir,
       'libs': libs,
       'includes': includes
      }

        f = open("config/Site.local", "w")
        f.write(cfgtxt)
        f.close()

        # generate Makefile
        cmd = "./config/ymkmf"
        run_cmd(cmd, log_all=True, simple=True)

    def build_step(self):
        """Building is done in install_step."""
        pass

    def install_step(self):
        """Build in install dir using build_step."""

        cmd = "make Everything"
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """
        Custom sanity check for NCL
        """
        custom_paths = {
            'files': ["bin/ncl", "lib/libncl.a", "lib/libncarg.a"],
            'dirs': ["include/ncarg"],
        }
        super(EB_NCL, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Set NCARG_ROOT environment variable in module."""
        txt = super(EB_NCL, self).make_module_extra()
        txt += self.module_generator.set_environment('NCARG_ROOT', self.installdir)
        return txt
