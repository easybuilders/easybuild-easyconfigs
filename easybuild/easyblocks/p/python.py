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
EasyBuild support for building and installing Python, implemented as an easyblock
"""

import os
import shutil

import easybuild.tools.toolkit as toolkit
from easybuild.framework.application import ApplicationPackage, Application
from easybuild.tools.filetools import unpack, patch, run_cmd
from easybuild.tools.modules import get_software_root


class eb_Python(Application):
    """Support for building/installing Python
    - default configure/make/make install works fine

    To extend Python by adding extra packages there are two ways:
    - list the packages in the pkglist, this will include the packages in this Python easyblock
    - create a seperate easyblock, so the packages can be loaded with module load

    e.g., you can include numpy and scipy in a default Python installation
    but also provide newer updated numpy and scipy versions by creating a PythonPackageModule for it.
    """

    def extra_packages_pre(self):
        """
        We set some default configs here for packages included in python
        """
        #insert new packages by building them with eb_DefaultPythonPackage
        self.log.debug("setting extra packages options")
        # use __name__ here, since this is the module where eb_DefaultPythonPackage is defined
        self.setcfg('pkgdefaultclass', (__name__, "eb_DefaultPythonPackage"))
        self.setcfg('pkgfilter', ('python -c "import %(name)s"', ""))

    def make_install(self):
        """Extend make install to make sure that the 'python' command is present."""
        Application.make_install(self)

        python_binary_path = os.path.join(self.installdir, 'bin', 'python')
        if not os.path.isfile(python_binary_path):
            pythonver = '.'.join(self.version().split('.')[0:2])
            srcbin = "%s%s" % (python_binary_path, pythonver)
            try:
                os.symlink(srcbin, python_binary_path)
            except OSError, err:
                self.log.error("Failed to symlink %s to %s: %s" % err)


class eb_DefaultPythonPackage(ApplicationPackage):
    """
    Easyblock for python packages to be included in the python installation.
    """

    def __init__(self, mself, pkg, pkginstalldeps):
        ApplicationPackage.__init__(self, mself, pkg, pkginstalldeps)
        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.sitecfglibdir = None
        self.sitecfgincdir = None
        self.testinstall = False
        self.builddir = mself.builddir
        self.mself = mself
        self.installopts = ''
        self.runtest = None
        self.pkgdir = "%s/%s" % (self.builddir, self.name)
        self.unpack_options = ''

        self.python = get_software_root('Python')

    def configure(self):
        """Configure Python package build
        """

        if self.sitecfg: # used by some packages, like numpy, to find certain libs
            finaltxt = self.sitecfg
            if self.sitecfglibdir:
                repl = self.sitecfglibdir
                finaltxt = finaltxt.replace('SITECFGLIBDIR', repl)

            if self.sitecfgincdir:
                repl = self.sitecfgincdir
                finaltxt = finaltxt.replace('SITECFGINCDIR', repl)

            self.log.debug("Using %s: %s" % (self.sitecfgfn, finaltxt))

            try:
                if os.path.exists(self.sitecfgfn):
                    txt = open(self.sitecfgfn).read()
                    self.log.debug("Found %s: %s" % (self.sitecfgfn, txt))
                config = open(self.sitecfgfn, 'w')
                config.write(finaltxt)
                config.close()
            except IOError:
                self.log.exception("Creating %s failed" % self.sitecfgfn)

    def make(self):
        """Build Python package via setup.py"""

        cmd = "python setup.py build "

        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """Install built Python package"""

        cmd = "python setup.py install --prefix=%s %s" % (self.python, self.installopts)
        run_cmd(cmd, log_all=True, simple=True)

    def test(self):
        """Test the compilation
        - default: None
        """
        extrapath = ""
        testinstalldir = os.path.join(self.builddir, "mytemporarytestinstalldir")
        if self.testinstall:
            # Install in test directory and export PYTHONPATH
            try:
                os.makedirs(testinstalldir)
            except OSError:
                self.log.exception("Creating testinstalldir %s failed" % testinstalldir)

            ppath = "%s/reallib" % testinstalldir
            cmd = "python setup.py install --install-scripts=%s --install-purelib=%s %s" % \
                (testinstalldir, ppath, self.installopts)
            run_cmd(cmd, log_all=True, simple=True)

            if os.environ.has_key('PYTHONPATH'):
                extrapath = "export PYTHONPATH=%s:%s && " % (ppath, os.environ['PYTHONPATH'])
            else:
                extrapath = "export PYTHONPATH=%s && " % ppath

        if self.runtest:
            cmd = "%s%s" % (extrapath, self.runtest)
            run_cmd(cmd, log_all=True, simple=True)

        if self.testinstall:
            try:
                shutil.rmtree(testinstalldir)
            except OSError, err:
                self.log.exception("Removing testinstalldir %s failed: %s" % (testinstalldir, err))

    def run(self):
        """Perform the actual package build/installation procedure"""

        # unpack
        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % \
                           (self.name, self.src))
        self.pkgdir = unpack("%s" % self.src, "%s/%s" % (self.builddir, self.name), extra_options=self.unpack_options)

        # patch if needed
        if self.patches:
            for patchfile in self.patches:
                if not patch(patchfile, self.pkgdir):
                    self.log.error("Applying patch %s failed" % patchfile)

        # configure, make, test, make install
        self.configure()
        self.make()
        self.test()
        self.make_install()

    def getcfg(self, *args, **kwargs):
        return self.mself.getcfg(*args, **kwargs)


class eb_Nose(eb_DefaultPythonPackage):
    """nose package"""
    def __init__(self, mself, pkg, pkginstalldeps):
        eb_DefaultPythonPackage.__init__(self, mself, pkg, pkginstalldeps)

        # use extra unpack options to avoid problems like
        # 'tar: Ignoring unknown extended header keyword `SCHILY.nlink'
        # and tar exiting with non-zero exit code
        self.unpack_options = ' --pax-option="delete=SCHILY.*" --pax-option="delete=LIBARCHIVE.*" '


class eb_FortranPythonPackage(eb_DefaultPythonPackage):
    """Extends eb_DefaultPythonPackage to add a Fortran compiler to the make call"""

    def make(self):
        comp_fam = self.toolkit().comp_family()

        if comp_fam == toolkit.INTEL:
            cmd = "python setup.py build --compiler=intel --fcompiler=intelem"

        elif comp_fam == toolkit.GCC:
            cmdprefix = ""
            ldflags = os.getenv('LDFLAGS')
            if ldflags:
                # LDFLAGS should not be set when building numpy/scipy, because it overwrites whatever numpy/scipy sets
                # see http://projects.scipy.org/numpy/ticket/182
                # don't unset it with os.environ.pop('LDFLAGS'), doesn't work in Python 2.4 (see http://bugs.python.org/issue1287)
                cmdprefix = "unset LDFLAGS && "
                self.log.debug("LDFLAGS was %s, will be cleared before numpy build with '%s'" % (ldflags, cmdprefix))

            cmd = "%s python setup.py build --fcompiler=gnu95" % cmdprefix

        else:
            self.log.error("Unknown family of compilers being used?")

        run_cmd(cmd, log_all=True, simple=True)


class eb_Numpy(eb_FortranPythonPackage):
    """numpy package"""

    def __init__(self, mself, pkg, pkginstalldeps):
        eb_FortranPythonPackage.__init__(self, mself, pkg, pkginstalldeps)

        self.pkgcfgs = mself.getcfg('pkgcfgs')
        if self.pkgcfgs.has_key('numpysitecfglibsubdirs'):
            self.numpysitecfglibsubdirs = self.pkgcfgs['numpysitecfglibsubdirs']
        else:
            self.numpysitecfglibsubdirs = []
        if self.pkgcfgs.has_key('numpysitecfgincsubdirs'):
            self.numpysitecfgincsubdirs = self.pkgcfgs['numpysitecfgincsubdirs']
        else:
            self.numpysitecfgincsubdirs = []

        self.sitecfg = """[DEFAULT]
library_dirs = %(libs)s
include_dirs = %(includes)s
search_static_first=True

"""

        if get_software_root("IMKL"):
            #use mkl
            extrasiteconfig = """[mkl]
lapack_libs = %(lapack)s
mkl_libs = %(blas)s
        """
        elif get_software_root("ATLAS") and get_software_root("LAPACK"):
            extrasiteconfig = """
[blas_opt]
libraries = %(blas)s
[lapack_opt]
libraries = %(lapack)s
        """
        else:
            self.log.error("Could not detect math kernel (mkl, atlas)")

        if get_software_root("IMKL") or get_software_root("FFTW"):
            extrasiteconfig += """
[fftw]
libraries = %s
        """ % os.getenv("LIBFFT")

        self.sitecfg = self.sitecfg + extrasiteconfig

        lapack_libs = os.getenv("LIBLAPACK_MT").split(" -l")
        blas_libs = os.getenv("LIBBLAS_MT").split(" -l")
        if get_software_root("IMKL"):
            # with IMKL, get rid of all spaces and use '-Wl:'
            lapack_libs.remove("pthread")
            lapack = ','.join(lapack_libs).replace(' ', ',').replace('Wl,','Wl:')
            blas = lapack
        else:
            lapack = ", ".join(lapack_libs)
            blas = ", ".join(blas_libs)

        self.sitecfg = self.sitecfg % \
            {
             'lapack': lapack,
             'blas': blas,
             'libs': ":".join([lib for lib in os.getenv('LDFLAGS').split(" -L")]),
             'includes': ":".join([lib for lib in os.getenv('CPPFLAGS').split(" -I")]),
            }

        self.sitecfgfn = 'site.cfg'
        self.installopts = ''
        self.testinstall = True
        self.runtest = "cd .. && python -c 'import numpy; numpy.test(verbose=2)'"

    def make_install(self):
        """Install numpy package
        We remove the numpy build dir here, so scipy doesn't find it by accident
        """
        eb_FortranPythonPackage.make_install(self)
        builddir = os.path.join(self.builddir, "numpy")
        if os.path.isdir(builddir):
            shutil.rmtree(builddir)
        else:
            self.log.debug("build dir %s already clean" % builddir)


class eb_Scipy(eb_FortranPythonPackage):
    """scipy package"""

    def __init__(self, mself, pkg, pkginstalldeps):
        eb_FortranPythonPackage.__init__(self, mself, pkg, pkginstalldeps)

        # disable testing
        test = False
        if test:
            self.testinstall = True
            self.runtest = "cd .. && python -c 'import numpy; import scipy; scipy.test(verbose=2)'"
        else:
            self.testinstall = False
            self.runtest = None

