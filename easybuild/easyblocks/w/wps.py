##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
from distutils.version import LooseVersion
import fileinput
import os
import re
import sys
from easybuild.framework.application import Application
from easybuild.tools.filetools import patch_perl_script_autoflush, run_cmd, run_cmd_qa
from easybuild.easyblocks.n.netcdf import set_netcdf_env_vars, get_netcdf_module_set_cmds

class WPS(Application):
    """Support for building/installing WPS."""

    def __init__(self):
        """Add extra config options specific to WPS."""

        Application.__init__(self)

        self.build_in_installdir = True

        self.cfg.update({'buildtype':[None, "Specify the type of build (smpar: OpenMP, dmpar: MPI)."]
                         })

    def configure(self):
        """Configure build: 
        - set required environment variables (for netCDF, JasPer)
        - patch compile script and ungrib Makefile for non-default install paths of WRF and JasPer
        - run configure script and figure how to select desired build option
        - patch configure.wps file afterwards to fix 'serial compiler' setting
        """

        # netCDF dependency check + setting env vars (NETCDF, NETCDFF)
        set_netcdf_env_vars(self.log)

        # WRF dependency check
        softrootwrf = os.getenv('SOFTROOTWRF')
        if softrootwrf:
            majver = os.getenv('SOFTVERSIONWRF').split('.')[0]
            self.wrfdir = os.path.join(softrootwrf, "WRFV%s" % majver)
        else:
            self.log.error("WRF module not loaded?")

        # patch compile script so that WRF is found
        self.compile_script = "compile"
        try:
            for line in fileinput.input(self.compile_script, inplace=1, backup='.orig.wrf'):
                line = re.sub(r"^(\s*set\s*WRF_DIR_PRE\s*=\s*)\${DEV_TOP}(.*)$", r"\1%s\2" % self.wrfdir, line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Failed to patch %s script: %s" % (self.compile_script, err))

        # libpng dependency check
        libpng = os.getenv('SOFTROOTLIBPNG')
        libpnginc = "%s/include" % libpng
        libpnglibdir = "%s/lib" % libpng
        if not libpng:
            self.log.error("libpng module not loaded?")

        # JasPer dependency check + setting env vars
        jasper = os.getenv('SOFTROOTJASPER')
        jasperlibdir = os.path.join(jasper, "lib")
        if jasper:
            os.putenv('JASPERINC', os.path.join(jasper, "include"))
            os.putenv('JASPERLIB', jasperlibdir)
        else:
            self.log.error("JasPer module not loaded?")

        # patch ungrib Makefile so that JasPer is found
        fn = os.path.join("ungrib","src","Makefile")
        jasperlibs = "-L%s -ljasper -L%s -lpng" % (jasperlibdir, libpnglibdir)
        try:
            for line in fileinput.input(fn, inplace=1, backup='.orig.JasPer'):
                line = re.sub(r"^(\s*-L\.\s*-l\$\(LIBTARGET\))(\s*;.*)$", r"\1 %s\2" % jasperlibs, line)
                line = re.sub(r"^(\s*\$\(COMPRESSION_LIBS\))(\s*;.*)$", r"\1 %s\2" % jasperlibs, line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Failed to patch %s: %s" % (fn, err))

        # patch arch/Config.pl script, so that run_cmd_qa receives all output to answer questions
        patch_perl_script_autoflush(os.path.join("arch", "Config.pl"))

        # configure

        # determine build type option to look for
        build_type_option = None

        if LooseVersion(self.version()) >= LooseVersion("3.4"):

            knownbuildtypes = {
                               'smpar':'serial',
                               'dmpar':'dmpar'
                               }

            if self.tk.toolkit_comp_family() == "Intel":
                build_type_option = " Linux x86_64, Intel compiler"

            elif self.tk.toolkit_comp_family() == "GCC":
                build_type_option = "Linux x86_64 g95 compiler"

            else:
                self.log.error("Don't know how to figure out build type to select.")

        else:

            knownbuildtypes = {
                               'smpar':'serial',
                               'dmpar':'DM parallel'
                               }

            if self.tk.toolkit_comp_family() == "Intel":
                build_type_option = "PC Linux x86_64, Intel compiler"

            elif self.tk.toolkit_comp_family() == "GCC":
                build_type_option = "PC Linux x86_64, gfortran compiler,"
                knownbuildtypes['dmpar'] = knownbuildtypes['dmpar'].upper()

            else:
                self.log.error("Don't know how to figure out build type to select.")

        # check and fetch selected build type
        bt = self.getcfg('buildtype')

        if not bt in knownbuildtypes.keys():
            self.log.error("Unknown build type: '%s'. Supported build types: %s" % (bt, knownbuildtypes.keys()))

        # fetch option number based on build type option and selected build type
        build_type_question = "\s*(?P<nr>[0-9]+).\s*%s\s*\(?%s\)?\s*\n" % (build_type_option, knownbuildtypes[bt])

        cmd = "./configure"
        qa = {}
        no_qa = []
        std_qa = {
                  # named group in match will be used to construct answer
                  r"%s(.*\n)*Enter selection\s*\[[0-9]+-[0-9]+\]\s*:" % build_type_question:"%(nr)s",
                  }

        run_cmd_qa(cmd, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

        # make sure correct compilers and compiler flags are being used
        comps = {
                 'SCC':"%s -I$(JASPERINC) -I%s" % (os.getenv('CC'), libpnginc),
                 'SFC':os.getenv('F90'),
                 'DM_FC':os.getenv('MPIF90'),
                 'DM_CC':os.getenv('MPICC'),
                 'FC':os.getenv('MPIF90'),
                 'CC':os.getenv('MPICC'),
                 }
        fn='configure.wps'
        for line in fileinput.input(fn, inplace=1,backup='.orig.comps'):
            for k,v in comps.items():
                line = re.sub(r"^(%s\s*=\s*).*$" % k, r"\1 %s" % v, line)
            sys.stdout.write(line)

    def make(self):
        """Building is performed in make_install."""
        pass

    def make_install(self):
        """Build in install dir using compile script."""

        cmd = "./%s" % self.compile_script
        run_cmd(cmd, log_all=True, simple=True)

    def sanitycheck(self):
        """Custom sanity check for WPS."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths',{'files':["WPS/%s"%x for x in ["geogrid.exe",
                                                                          "metgrid.exe",
                                                                          "ungrib.exe"]],
                                            'dirs':[]
                                            })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def make_module_req_guess(self):
        """Make sure PATH and LD_LIBRARY_PATH are set correctly."""

        return {
            'PATH': [self.name()],
            'LD_LIBRARY_PATH': [self.name()],
            'MANPATH': [],
        }

    def make_module_extra(self):
        """Add netCDF environment variables to module file."""

        txt = Application.make_module_extra(self)

        txt += get_netcdf_module_set_cmds(self.log)

        return txt