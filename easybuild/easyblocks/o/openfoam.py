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
EasyBuild support for building and installing OpenFOAM, implemented as an easyblock
"""
import os
import stat
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolkit as toolkit
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, adjust_permissions
from easybuild.tools.modules import get_software_root


class eb_OpenFOAM(Application):
    """Support for building and installing OpenFOAM."""

    def __init__(self,*args,**kwargs):
        """Specify that OpenFOAM should be built in install dir."""

        Application.__init__(self, *args, **kwargs)

        self.build_in_installdir = True

        self.wm_compiler= None
        self.wm_mplib = None
        self.mpipath = None
        self.thrdpartydir = None

    def configure(self):
        """Configure OpenFOAM build by setting appropriate environment variables."""

        # installation directory
        env.set("FOAM_INST_DIR", self.installdir)

        # third party directory
        self.thrdpartydir = "ThirdParty-%s" % self.version()
        os.symlink(os.path.join("..", self.thrdpartydir), self.thrdpartydir)
        env.set("WM_THIRD_PARTY_DIR", os.path.join(self.installdir, self.thrdpartydir))

        # compiler
        comp_fam = self.toolkit().comp_family()

        if comp_fam == toolkit.GCC:
            self.wm_compiler="Gcc"

        elif comp_fam == toolkit.INTEL:
            self.wm_compiler="Icc"

            # make sure -no-prec-div is used with Intel compilers
            self.updatecfg('premakeopts', 'CFLAGS="$CFLAGS -no-prec-div" CXXFLAGS="$CXXFLAGS -no-prec-div"')

        else:
            self.log.error("Unknown compiler family, don't know how to set WM_COMPILER")

        env.set("WM_COMPILER",self.wm_compiler)

        # type of MPI
        mpi_type = self.toolkit().mpi_type()

        if mpi_type == toolkit.INTEL:
            self.mpipath = os.path.join(get_software_root('IMPI'),'intel64')
            self.wm_mplib = "IMPI"

        elif mpi_type == toolkit.QLOGIC:
            self.mpipath = get_software_root('QLogicMPI')
            self.wm_mplib = "MPICH"

        elif mpi_type == toolkit.OPENMPI:
            self.mpipath = get_software_root('OpenMPI')
            self.wm_mplib = "MPI-MVAPICH2"

        else:
            self.log.error("Unknown MPI, don't know how to set MPI_ARCH_PATH, WM_MPLIB or FOAM_MPI_LIBBIN")

        env.set("WM_MPLIB", self.wm_mplib)
        env.set("MPI_ARCH_PATH", self.mpipath)
        env.set("FOAM_MPI_LIBBIN", self.mpipath)

        # parallel build spec
        env.set("WM_NCOMPPROCS", str(self.getcfg('parallel')))

    def make(self):
        """Build OpenFOAM using make after sourcing script to set environment."""

        nameversion = "%s-%s"%(self.name(), self.version())

        precmd = "source %s" % os.path.join(self.builddir, nameversion, "etc", "bashrc")

        # make directly in install directory
        cmd="%(precmd)s && %(premakeopts)s %(makecmd)s"%{'precmd':precmd,
                                                         'premakeopts':self.getcfg('premakeopts'),
                                                         'makecmd':os.path.join(self.builddir, nameversion, "Allwmake")}
        run_cmd(cmd,log_all=True,simple=True,log_output=True)

    def make_install(self):
        """Building was performed in install dir, so just fix permissions."""

        # fix permissions of various OpenFOAM-x subdirectories (only known to be required for v1.x)
        if LooseVersion(self.version()) <= LooseVersion('2'):
            installPath = "%s/%s-%s"%(self.installdir, self.name(), self.version())

            for d in ["applications", "bin", "doc", "etc", "lib", "src", "tutorials"]:
                # Make directories readable and executable for others
                fullpath = os.path.join(installPath, d)
                adjust_permissions(fullpath, stat.S_IROTH|stat.S_IXOTH, add=True)

        # fix permissions of ThirdParty dir and subdirs (also for 2.x)
        fullpath = os.path.join(self.installdir, self.thrdpartydir)
        adjust_permissions(fullpath, stat.S_IROTH|stat.S_IXOTH, add=True, recursive=False)
        for d in ["etc", "platforms"]:
            fullpath = os.path.join(self.installdir, self.thrdpartydir, d)
            adjust_permissions(fullpath, stat.S_IROTH|stat.S_IXOTH, add=True)

    def sanitycheck(self):
        """Custom sanity check for OpenFOAM"""

        if not self.getcfg('sanityCheckPaths'):

            odir = "%s-%s" % (self.name(), self.version())

            psubdir = "linux64%sDPOpt" % self.wm_compiler

            if LooseVersion(self.version()) < LooseVersion("2"):
                toolsdir = os.path.join(odir, "applications", "bin", psubdir)

            else:
                toolsdir = os.path.join(odir, "platforms", psubdir, "bin")

            pdirs = []
            if LooseVersion(self.version()) >= LooseVersion("2"):
                pdirs = [toolsdir, os.path.join(odir, "platforms", psubdir, "lib")]

            # some randomly selected binaries
            # if one of these is missing, it's very likely something went wrong
            bins = [os.path.join(odir, "bin", x) for x in []] + \
                   [os.path.join(toolsdir, "buoyant%sSimpleFoam" % x) for x in ["", "Boussinesq"]] + \
                   [os.path.join(toolsdir, "%sFoam" % x) for x in ["bubble", "engine", "sonic"]] + \
                   [os.path.join(toolsdir, "surface%s" % x) for x in ["Add", "Find", "Smooth"]] + \
                   [os.path.join(toolsdir, x) for x in ["deformedGeom", "engineSwirl", "modifyMesh", "refineMesh", "vorticity"]]

            self.setcfg('sanityCheckPaths',{'files':["%s/etc/%s" % (odir, x) for x in ["bashrc", "cshrc"]] + bins,
                                            'dirs':pdirs
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def make_module_extra(self):
        """Define extra environment variables required by OpenFOAM"""

        txt = Application.make_module_extra(self)

        env_vars = [("WM_PROJECT_VERSION", self.version()),
                    ("FOAM_INST_DIR", "$root"),
                    ("WM_COMPILER", self.wm_compiler),
                    ("WM_MPLIB", self.wm_mplib),
                    ("MPI_ARCH_PATH", self.mpipath),
                    ("FOAM_BASH", "$root/%s-%s/etc/bashrc" % (self.name(), self.version())),
                    ("FOAM_CSH", "$root/%s-%s/etc/cshrc" % (self.name(), self.version())),
                    ]

        for env_var in env_vars:
            txt += "setenv\t%s\t%s\n" % env_var

        return txt
