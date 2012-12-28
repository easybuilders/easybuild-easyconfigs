##
# Copyright 2009-2012 Ghent University
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for Python, implemented as an easyblock
"""

import os
import re
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.extension import Extension
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_patch, extract_file, rmtree2, run_cmd
from easybuild.tools.modules import get_software_root


class EB_Python(ConfigureMake):
    """Support for building/installing Python
    - default configure/build_step/make install works fine

    To extend Python by adding extra packages there are two ways:
    - list the packages in the exts_list, this will include the packages in this Python installation
    - create a seperate easyblock, so the packages can be loaded with module load

    e.g., you can include numpy and scipy in a default Python installation
    but also provide newer updated numpy and scipy versions by creating a PythonPackage-derived easyblock for it.
    """

    def prepare_for_extensions(self):
        """
        We set some default configs here for packages included in Python
        """
        #insert new packages by building them with EB_DefaultPythonPackage
        self.log.debug("setting extra packages options")
        # use __name__ here, since this is the module where EB_DefaultPythonPackage is defined
        self.cfg['exts_defaultclass'] = (__name__, "EB_DefaultPythonPackage")
        self.cfg['exts_filter'] = ('python -c "import %(name)s"', "")

    def configure_step(self):
        """Set extra configure options."""
        self.cfg.update('configopts', "--with-threads --enable-shared")

        super(EB_Python, self).configure_step()

    def install_step(self):
        """Extend make install to make sure that the 'python' command is present."""
        super(EB_Python, self).install_step()

        python_binary_path = os.path.join(self.installdir, 'bin', 'python')
        if not os.path.isfile(python_binary_path):
            pythonver = '.'.join(self.version.split('.')[0:2])
            srcbin = "%s%s" % (python_binary_path, pythonver)
            try:
                os.symlink(srcbin, python_binary_path)
            except OSError, err:
                self.log.error("Failed to symlink %s to %s: %s" % err)

    def sanity_check_step(self):
        """Custom sanity check for Python."""

        pyver = "python%s" % '.'.join(self.version.split('.')[0:2])

        try:
            self.load_fake_module()
        except EasyBuildError, err:
            self.log.debug("Loading fake module failed: %s" % err)

        abiflags = ''
        if LooseVersion(self.version) >= LooseVersion("3"):
            run_cmd("which python", log_all=True, simple=False)
            cmd = 'python -c "import sysconfig; print(sysconfig.get_config_var(\'abiflags\'));"'
            (abiflags, _) = run_cmd(cmd, log_all=True, simple=False)
            if not abiflags:
                self.log.error("Failed to determine abiflags: %s" % abiflags)
            else:
                abiflags = abiflags.strip()

        custom_paths = {
                        'files':["bin/%s" % pyver, "lib/lib%s%s.so" % (pyver, abiflags)],
                        'dirs':["include/%s%s" % (pyver, abiflags), "lib/%s" % pyver]
                       }

        super(EB_Python, self).sanity_check_step(custom_paths=custom_paths)

class EB_DefaultPythonPackage(Extension):
    """
    Easyblock for Python packages to be included in the Python installation.
    """

    def __init__(self, mself, ext):
        super(EB_DefaultPythonPackage, self).__init__(mself, ext)
        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.sitecfglibdir = None
        self.sitecfgincdir = None
        self.testinstall = False
        self.builddir = mself.builddir
        self.mself = mself
        self.installopts = ''
        self.runtest = None
        self.ext_dir = "%s/%s" % (self.builddir, self.name)
        self.unpack_options = ''

        self.python = get_software_root('Python')

    def configure_step(self):
        """Configure Python package build
        """

        if self.sitecfg: # used by some extensions_step, like numpy, to find certain libs
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

    def build_step(self):
        """Build Python package via setup.py"""

        cmd = "python setup.py build "

        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install built Python package"""

        cmd = "python setup.py install --prefix=%s %s" % (self.python, self.installopts)
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
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
                rmtree2(testinstalldir)
            except OSError, err:
                self.log.exception("Removing testinstalldir %s failed: %s" % (testinstalldir, err))

    def run(self):
        """Perform the actual Python package build/installation procedure"""

        # extract_file
        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % \
                           (self.name, self.src))
        self.ext_dir = extract_file("%s" % self.src, "%s/%s" % (self.builddir, self.name), extra_options=self.unpack_options)

        # patch if needed
        if self.patches:
            for patchfile in self.patches:
                if not apply_patch(patchfile, self.ext_dir):
                    self.log.error("Applying patch %s failed" % patchfile)

        # configure, build_step, test, make install
        self.configure_step()
        self.build_step()
        self.test_step()
        self.install_step()


class EB_nose(EB_DefaultPythonPackage):
    """Support for installing the nose Python package as part of a Python installation."""

    def __init__(self, mself, ext):

        super(EB_nose, self).__init__(mself, ext)

        # use extra unpack options to avoid problems like
        # 'tar: Ignoring unknown extended header keyword `SCHILY.nlink'
        # and tar exiting with non-zero exit code
        self.unpack_options = ' --pax-option="delete=SCHILY.*" --pax-option="delete=LIBARCHIVE.*" '


class EB_FortranPythonPackage(EB_DefaultPythonPackage):
    """Extends EB_DefaultPythonPackage to add a Fortran compiler to the make call"""

    def build_step(self):
        comp_fam = self.toolchain.comp_family()

        if comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
            cmd = "python setup.py build --compiler=intel --fcompiler=intelem"

        elif comp_fam == toolchain.GCC:  #@UndefinedVariable
            cmdprefix = ""
            ldflags = os.getenv('LDFLAGS')
            if ldflags:
                # LDFLAGS should not be set when building numpy/scipy, because it overwrites whatever numpy/scipy sets
                # see http://projects.scipy.org/numpy/ticket/182
                # don't unset it with os.environ.pop('LDFLAGS'), doesn't work in Python 2.4 (see http://bugs.python.org/issue1287)
                cmdprefix = "unset LDFLAGS && "
                self.log.debug("LDFLAGS was %s, will be cleared before %s build with '%s'" % (self.name,
                                                                                              ldflags,
                                                                                              cmdprefix))

            cmd = "%s python setup.py build --fcompiler=gnu95" % cmdprefix

        else:
            self.log.error("Unknown family of compilers being used?")

        run_cmd(cmd, log_all=True, simple=True)


class EB_numpy(EB_FortranPythonPackage):
    """Support for installing the numpy Python package as part of a Python installation."""

    def __init__(self, mself, ext):
        super(EB_numpy, self).__init__(mself, ext)

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
        """ % os.getenv("LIBFFT").replace(' ', ',')

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
             'libs': ':'.join(self.toolchain.get_variable('LDFLAGS', typ=list)),
             'includes': ':'.join(self.toolchain.get_variable('CPPFLAGS', typ=list))
            }

        self.sitecfgfn = 'site.cfg'
        self.installopts = ''
        self.testinstall = True
        self.runtest = "cd .. && python -c 'import numpy; numpy.test(verbose=2)'"

    def install_step(self):
        """Install numpy 
        We remove the numpy build dir here, so scipy doesn't find it by accident
        """
        super(EB_numpy, self).install_step()
        builddir = os.path.join(self.builddir, "numpy")
        if os.path.isdir(builddir):
            rmtree2(builddir)
        else:
            self.log.debug("build dir %s already clean" % builddir)


class EB_scipy(EB_FortranPythonPackage):
    """Support for installing the scipy Python package as part of a Python installation."""

    def __init__(self, mself, ext):
        super(EB_scipy, self).__init__(mself, ext)

        # disable testing
        test = False
        if test:
            self.testinstall = True
            self.runtest = "cd .. && python -c 'import numpy; import scipy; scipy.test(verbose=2)'"
        else:
            self.testinstall = False
            self.runtest = None

