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
from easybuild.tools.filetools import run_cmd, run_cmd_qa

class WRF(Application):
    """Support for building/installing WRF."""

    def __init__(self,*args,**kwargs):
        """Add extra config options specific to WRF."""

        Application.__init__(self, args,kwargs)
        
        self.build_in_installdir = True

        self.cfg.update({'wrfbuildtype':[None, "Specify the type of build (smpar: OpenMP, dmpar: MPI, dm+sm: hybrid OpenMP/MPI)."],
                         'rewriteopts':[True, "Replace default -O3 option in configure.wrf with CFLAGS/FFLAGS from environment (default: True)."]})

    def configure(self):        
        """Configure build: 
            - set some magic environment variables
            - run configure script
            - adjust configure.wrf file if needed
        """

        # netCDF dependency
        netcdf = os.getenv('SOFTROOTNETCDF')
        if not netcdf:
            self.log.error("netCDF module not loaded?")
        else:
            os.putenv('NETCDF', netcdf)
            netcdff = os.getenv('SOFTROOTNETCDFMINFORTRAN')
            netcdff_ver = os.getenv('SOFTVERSIONNETCDFMINFORTRAN')
            if not netcdff and LooseVersion(netcdff_ver) >= LooseVersion("4.2"):
                self.log.error("netCDF v4.2 no longer supplies Fortran library, also need netCDF-Fortran")
            else:
                os.putenv('NETCDFF', netcdff)

        # HDF5 (optional) dependency
        hdf5 = os.getenv('SOFTROOTHDF5')
        if hdf5:
            # check if this is parallel HDF5
            phdf5_bins = ['h5pcc','ph5diff']
            parallel_hdf5 = True
            for f in phdf5_bins:
                if not os.path.exists(os.path.join(hdf5, 'bin', f)):
                    parallel_hdf5 = False
                    break
            if not (hdf5 or parallel_hdf5):
                self.log.error("Parallel HDF5 module not loaded?")
            else:
                os.putenv('PHDF5', hdf5)
        else:
            self.log.info("HDF5 module not loaded, assuming that's OK...")

        # enable support for large file support in netCDF
        os.putenv('WRFIO_NCD_LARGE_FILE_SUPPORT', '1')

        # build type
        knownbuildtypes = {'smpar':10,
                           'dmpar':11,
                           'dm+sm':12}

        bt = self.getcfg('wrfbuildtype')

        if not bt in knownbuildtypes.keys():
            self.log.error("Unknown build type: '%s'. Supported build types: %s" % (bt, knownbuildtypes))

        # run configure script
        cmd = "./configure"
        qa = {}
        no_qa = []
        # hackish way of delivering answers to interactive installer
        # specifying questions to answer proved to be difficult (incomplete output?)
        std_qa = {r"\)":"%s" % knownbuildtypes[bt],
                  r"[-]+":"1"
                 }

        run_cmd_qa(cmd, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

        # rewrite optimization options if desired
        if self.getcfg('rewriteopts'):

            ## replace default -O3 option in configure.wrf with CFLAGS/FFLAGS from environment
            fn='configure.wrf'

            self.log.info("Rewriting optimization options in %s" % fn)

            # set extra flags for Intel compilers
            # see http://software.intel.com/en-us/forums/showthread.php?t=72109&p=1#146748
            if os.getenv('SOFTROOTICC') or os.getenv('SOFTROOTIFORT'):

                # -O3 -heap-arrays is required to resolve compilation error
                for envvar in ['CFLAGS', 'FFLAGS']:
                    val = os.getenv(envvar)
                    if '-O3' in val:
                        os.environ[envvar] = '%s -heap-arrays' % val
                        self.log.info("Updated %s to '%s'" % (envvar, os.getenv(envvar)))

            # replace -O3 with desired optimization options
            for line in fileinput.input(fn, inplace=1, backup='orig.rewriteopts'):
                line = re.sub(r"^(FCOPTIM.*)(\s-O3)(\s.*)$", r"\1 %s \3" % os.getenv('FFLAGS'), line)
                line = re.sub(r"^(CFLAGS_LOCAL.*)(\s-O3)(\s.*)$", r"\1 %s \3" % os.getenv('CFLAGS'), line)
                sys.stdout.write(line)

    # building is done in make_install
    def make(self):
        pass

    def make_install(self):
        """Build and install WRF and testcases using provided compile script."""

        # enable parallel build
        p = self.getcfg('parallel')
        par = ""
        if p:
            par="-j %s"%p

        # build wrf
        cmd="./compile %s wrf" % (par)
        run_cmd(cmd, log_all=True, simple=True)

        # also build WRF test cases
        testcases=["em_b_wave","em_heldsuarez","em_les","em_quarter_ss","em_real","em_scm_xy",
                   "em_tropical_cyclone"]
        testcases2d=["em_grav2d_x","em_hill2d_x","em_seabreeze2d_x","em_squall2d_x","em_squall2d_y"]

        if not self.getcfg('wrfbuildtype') in ["dmpar","smpar","dm+sm"]:
            testcases += testcases2d

        for part in testcases:
            cmd="./compile %s %s"%(par,part)
            run_cmd(cmd, log_all=True, simple=True)

    def sanitycheck(self):
        """Custom sanity check for WRF."""

        if not self.getcfg('sanityCheckPaths'):

            mainver = self.version().split('.')[0]
            self.wrfsubdir = "WRFV%s"%mainver

            fs = ["libwrflib.a","wrf.exe","ideal.exe","real.exe","ndown.exe","nup.exe","tc.exe"]
            ds = ["main","run"]

            self.setcfg('sanityCheckPaths',{'files':[os.path.join(self.wrfsubdir,"main",x) for x in fs],
                                            'dirs':[os.path.join(self.wrfsubdir,x) for x in ds]
                                            })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)