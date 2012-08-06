##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
"""

import fileinput
import os
import re
import sys
from distutils.version import LooseVersion

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root


class NCL(Application):
    """Support for building/installing NCL."""

    def configure(self):
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
            self.log.error("Failed to change to the 'config' dir: %s" % err)

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
        if os.getenv('SOFTROOTIFORT'):
            if LooseVersion(os.getenv('SOFTVERSIONIFORT')) < LooseVersion('2011.4'):
                ctof_libs = '-lm -L${SOFTROOTIFORT}/lib/intel64 -lifcore -lifport'
            else:
                ctof_libs = '-lm -L${SOFTROOTIFORT}/compiler/lib/intel64 -lifcore -lifport'
        elif os.getenv('SOFTROOTGCC'):
            ctof_libs = '-lgfortran -lm'
        macrodict = {
                     'CCompiler': os.getenv('CC'),
                     'FCompiler': os.getenv('F77'),
                     'CcOptions': '-ansi %s' % os.getenv('CFLAGS'),
                     'FcOptions': os.getenv('FFLAGS'),
                     'COptimizeFlag': os.getenv('CFLAGS'),
                     'FOptimizeFlag': os.getenv('FFLAGS'),
                     'ExtraSysLibraries': os.getenv('LDFLAGS'),
                     'CtoFLibraries': ctof_libs
                    }

        # replace config entries that are already there
        for line in fileinput.input(cfg_filename, inplace=1, backup='%s.orig' % cfg_filename):
            for key,val in macrodict.items():
                regexp = re.compile("(#define %s\s*).*" % key)
                match = regexp.search(line)
                if match:
                    line = "#define %s %s\n" % (key, val)
                    macrodict.pop(key)
            sys.stdout.write(line)

        # add remaining config entries
        f = open(cfg_filename, "a")
        for key,val in macrodict.items():
            f.write("#define %s %s\n" % (key, val))
        f.close()

        f = open(cfg_filename, "r")
        self.log.debug("Contents of %s: %s" % (cfg_filename, f.read()))
        f.close()

        # configure
        try:
            os.chdir(self.getcfg('startfrom'))
        except OSError, err:
            self.log.error("Failed to change to the build dir %s: %s" % (self.getcfg('startfrom'), err))

        # instead of running the Configure script that asks a zillion questions,
        # let's just generate the config/Site.local file ourselves...

        # order of deps is important
        # HDF needs to go after netCDF, because both have a netcdf.h include file
        deps = ["HDF5", "JasPer", "netCDF", "HDF", "g2lib", "g2clib", "Szip"]

        libs = ''
        includes = ''
        for dep in deps:
            softroot = get_software_root(dep)
            if not softroot:
                self.log.error('%s not available' % dep)
            libs += ' -L%s/lib ' % softroot
            includes += ' -I%s/include ' % softroot

        cfgtxt="""#ifdef FirstSite
#endif /* FirstSite */

#ifdef SecondSite

#define YmakeRoot %(installdir)s

#define LibSearch %(libs)s
#define IncSearch %(includes)s

#define BuildNCL 1
#define HDFlib
#define HDFEOSlib
#define UdUnitslib
#define BuildGRIB2 1

#define BuildRasterHDF 0
#define BuildHDF4 0
#define BuildTRIANGLE 0
#define BuildUdunits 0
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

    def make(self):
        """Building is done in make_install."""
        pass

    def make_install(self):
        """Build in install dir using make."""

        cmd = "make Everything"
        run_cmd(cmd, log_all=True, simple=True)

    def make_module_extra(self):
        """Set NCARG_ROOT environment variable in module."""

        txt = Application.make_module_extra(self)
        txt += "setenv\tNCARG_ROOT\t$root\n"

        return txt
