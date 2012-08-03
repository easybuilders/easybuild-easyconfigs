##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
import os
import stat
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, recursiveChmod
import easybuild.tools.toolkit as toolkit


class OpenFOAM(Application):
    """Support for building and installing OpenFOAM."""

    def __init__(self,*args,**kwargs):
        """Specify that OpenFOAM should be built in install dir."""

        Application.__init__(self, *args, **kwargs)

        self.build_in_installdir = True

        self.wm_compiler= None
        self.wm_mplib = None
        self.mpipath = None

    def configure(self):
        """Configure OpenFOAM build by setting appropriate environment variables."""

        # installation directory
        os.putenv("FOAM_INST_DIR", self.installdir)

        # third party directory
        thrdpartydir = "ThirdParty-%s" % self.version()
        os.symlink(os.path.join("..", thrdpartydir), thrdpartydir)
        os.putenv("WM_THIRD_PARTY_DIR", os.path.join(self.installdir, thrdpartydir))

        # compiler
        comp_fam = self.tk.toolkit_comp_family()

        if comp_fam == toolkit.GCC:
            self.wm_compiler="Gcc"

        elif comp_fam == toolkit.INTEL:
            self.wm_compiler="Icc"

            # make sure -no-prec-div is used with Intel compilers
            self.updatecfg('premakeopts', 'CFLAGS="$CFLAGS -no-prec-div" CXXFLAGS="$CXXFLAGS -no-prec-div"')

        else:
            self.log.error("Unknown compiler family, don't know how to set WM_COMPILER")

        os.putenv("WM_COMPILER",self.wm_compiler)

        # type of MPI
        mpi_type = self.tk.toolkit_mpi_type()

        if mpi_type == toolkit.INTEL:
            self.mpipath = os.path.join(os.environ['SOFTROOTIMPI'],'intel64')
            self.wm_mplib = "IMPI"

        elif mpi_type == toolkit.QLOGIC:
            self.mpipath = os.environ['SOFTROOTQLOGICMPI']
            self.wm_mplib = "MPICH"

        else:
            self.log.error("Unknown MPI, don't know how to set MPI_ARCH_PATH, WM_MPLIB or FOAM_MPI_LIBBIN")

        os.putenv("WM_MPLIB", self.wm_mplib)
        os.putenv("MPI_ARCH_PATH", self.mpipath)
        os.putenv("FOAM_MPI_LIBBIN", self.mpipath)

        # parallel build spec
        os.putenv("WM_NCOMPPROCS", str(self.getcfg('parallel')))

    def make(self):
        """Building is done in make_install."""
        pass

    def make_install(self):
        """Build and install OpenFOAM."""

        nameversion = "%s-%s"%(self.name(), self.version())

        precmd = "source %s" % os.path.join(self.builddir, nameversion, "etc", "bashrc")

        # make directly in install directory
        cmd="%(precmd)s && %(premakeopts)s %(makecmd)s"%{'precmd':precmd,
                                                         'premakeopts':self.getcfg('premakeopts'),
                                                         'makecmd':os.path.join(self.builddir, nameversion, "Allwmake")}
        run_cmd(cmd,log_all=True,simple=True,log_output=True)

        # fix file permissions of various files (only known to be required for v1.x)
        if LooseVersion(self.version()) <= LooseVersion('2'):
            installPath = "%s/%s-%s"%(self.installdir, self.name(), self.version())

            for path in ["applications", "bin", "doc", "etc", "lib", "src", "tutorials"]:
                # Make directories readable for others
                recursiveChmod(os.path.join(installPath, path), stat.S_IROTH, add=True)

            for path in ["applications", "bin", "lib"]:
                # Make directories executable for others
                recursiveChmod(os.path.join(installPath, path), stat.S_IXOTH, add=True)

    def sanitycheck(self):
        """Custom sanity check for OpenFOAM"""

        if not self.getcfg('sanityCheckPaths'):

            odir = "%s-%s" % (self.name(), self.version())

            pdirs = []
            if LooseVersion(self.version()) >= LooseVersion("2"):
                pdirs = ["%s/platforms/linux64%sDPOpt/%s" % (odir, self.wm_compiler, x) for x in ["bin", "lib"]]

            self.setcfg('sanityCheckPaths',{'files':["%s/etc/%s" % (odir, x) for x in ["bashrc", "cshrc"]],
                                            'dirs':["%s/bin" % odir] + pdirs
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
