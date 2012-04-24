"""
Python easyblock
"""
from easybuild.framework.application import ApplicationPackage, Application
from easybuild.tools.filetools import unpack, patch, run_cmd
from shutil import SpecialFileError, ExecError
import os
import shutil

class Python(Application):
    """
    This is the python easyblock
    To extend python by adding extra packages there are two ways:
    - list the packages in the pkglist, this will include the packages in this python easyblock
    - create a seperate easyblock, so the packages can be loaded with module load
    
    e.g., you can include numpy and scipy in a default python install
    but also provide newer updated numpy and scipy versions by creating a PythonPackageModule for it.
    """
    def extra_packages_pre(self):
        """
        We set some default configs here for packages included in python
        """
        #insert new packages by  building them with DefaultPythonPackage
        self.log.debug("setting extra packages options")
        # use __name__ here, since this is the module where DefaultPythonPackage is defined
        self.setcfg('pkgdefaultclass', (__name__, "DefaultPythonPackage"))
        self.setcfg('pkgfilter', ('python -c "import %(name)s"', ""))

class DefaultPythonPackage(ApplicationPackage):
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
        self.cfg = mself.cfg
        self.installopts = ''
        self.runtest = None
        self.pkgdir = "%s/%s" % (self.builddir, self.name)

    def configure(self):
        """
        configure step
        """
        if self.sitecfg: #used by some packages, like numpy, to find certain libs
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
        """Use setup.py to make python packages."""
        if  "SOFTROOTICC" in os.environ :
            cmd = "python setup.py build --compiler=intel "
        else:
            cmd = "python setup.py build "

        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """
        install step
        """
        if not os.environ.has_key('SOFTROOTPYTHON'):
            self.log.error("Couldn't find SOFTROOTPYTHON variable")

        cmd = "python setup.py install --skip-build --prefix=%s %s" % (os.environ['SOFTROOTPYTHON'], self.installopts)
        run_cmd(cmd, log_all=True, simple=True)

    def test(self):
        """
        Test the compilation
        - default: None
        """
        extrapath = ""
        testinstalldir = os.path.join(self.builddir, "mytemporarytestinstalldir")
        if self.testinstall:
            #Install in test directory and export PYTHONPATH
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
            except (OSError, SpecialFileError, ExecError):
                self.log.exception("Removing testinstalldir %s failed" % testinstalldir)

    def run(self):
        # unpack
        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % \
                           (self.name, self.src))
        self.pkgdir = unpack("%s" % self.src, "%s/%s" % (self.builddir, self.name))
        # patch if needed
        if self.patches:
            for patchfile in self.patches:
                if not patch(patchfile, self.pkgdir):
                    self.log.error("Applying patch %s failed" % patchfile)

        # configure, make, make tes, make install
        self.configure()
        self.make()
        self.test()
        self.make_install()

class FortranPythonPackage(DefaultPythonPackage):
    """Extends DefaultPythonPackage to add a fortran compiler to the make call"""
    def make(self):
        if  "SOFTROOTICC" in os.environ and "SOFTROOTIFORT" in os.environ:
            cmd = "python setup.py build --compiler=intel --fcompiler=intelem"
        else:
            self.log.debug("LDFLAGS was %s now cleared" % os.environ.pop('LDFLAGS'))
            self.log.debug("LDFLAGS is now %s " % os.getenv("LDFLAGS", "cleared"))
            cmd = "python setup.py build  "

        run_cmd(cmd, log_all=True, simple=True)

class Numpy(FortranPythonPackage):
    """
    numpy package
    """
    def __init__(self, mself, pkg, pkginstalldeps):
        DefaultPythonPackage.__init__(self, mself, pkg, pkginstalldeps)

        self.pkgcfgs = self.cfg['pkgcfgs'][0]
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

        if  "SOFTROOTIMKL" in os.environ:
            #use mkl
            extrasiteconfig = """[mkl]
lapack_libs = '%(lapack)s'
mkl_libs = '%(blas)s '
        """
        elif "SOFTROOTATLAS" in os.environ and "SOFTROOTLAPACK" in os.environ:
            extrasiteconfig = """
[blas_opt]
libraries = '%(blas)s'
[lapack_opt]
libraries = '%(lapack)s'
        """
        else:
            self.log.error("Could not detect math kernel (mkl, atlas)")

        if "SOFTROOTIMKL" in os.environ or "SOFTROOTFFTW" in os.environ:
            extrasiteconfig += """ 
[fftw]
libraries ='%s'
        """ % os.getenv("LIBFFT")
        self.sitecfg = self.sitecfg + extrasiteconfig
        self.sitecfg = self.sitecfg % \
            { 'lapack' : ", ".join([lib for lib in os.getenv("LIBLAPACK_MT").split(" -l")]) ,
              'blas' : ", ".join([lib for lib in os.getenv("LIBBLAS_MT").split(" -l")]),
              'libs' : ":".join([lib for lib in os.getenv('LDFLAGS').split(" -L")]),
              'includes' : ":".join([lib for lib in os.getenv('CPPFLAGS').split(" -I")]),
            }

        self.sitecfgfn = 'site.cfg'
        self.installopts = ''
        self.testinstall = True
        self.runtest = "cd .. && python -c 'import numpy; numpy.test(verbose=2)'"

    def make_install(self):
        """
        install step
        We remove the numpy build dir here, so scipy doesn't find it by accident
        """
        FortranPythonPackage.make_install(self)
        builddir = os.path.join(self.builddir, "numpy")
        if os.path.isdir(builddir):
            shutil.rmtree()
        else:
            self.log.debug("build dir %s already clean" % builddir)


class Scipy(FortranPythonPackage):
    def __init__(self, mself, pkg, pkginstalldeps):
        DefaultPythonPackage.__init__(self, mself, pkg, pkginstalldeps)

        #disable testing
        test = False
        if test:
            self.testinstall = True
            self.runtest = "cd .. && python -c 'import numpy; import scipy; scipy.test(verbose=2)'"
        else:
            self.testinstall = False
            self.runtest = None

