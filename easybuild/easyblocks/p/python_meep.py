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
EasyBuild support for python-meep, implemented as an easyblock
"""
import glob
import os
import shutil
import tempfile

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, unpack
from easybuild.tools.modules import get_software_root, get_software_version


class EB_python_minus_meep(Application):
    """
    Support for building and installing python-meep
    """

    def __init__(self, *args, **kwargs):
        """Initialize custom variables."""
        Application.__init__(self, *args, **kwargs)

        # template for Python packages lib dir
        self.pylibdir = os.path.join("lib", "python%s", "site-packages")

    def configure(self):
        """Just check whether dependencies (Meep, Python) are available."""

        # complete Python packages lib dir
        pythonver = ".".join(get_software_version('Python').split(".")[0:2])
        self.pylibdir = self.pylibdir % pythonver

        # make sure that required dependencies are loaded
        deps = ["Meep", "Python"]
        for dep in deps:
            if not get_software_root(dep):
                self.log.error("Module for %s not loaded." % dep)

    def make(self):
        """Build python-meep using available make/make-mpi script."""

        # determine make script arguments
        meep = get_software_root('Meep')
        meepinc = os.path.join(meep, 'include')
        meeplib = os.path.join(meep, 'lib')
        numpyinc = os.path.join(get_software_root('Python'), self.pylibdir, 'numpy', 'core', 'include')

        # determine suffix for make script
        suff = ''
        if self.toolkit().opts['usempi']:
            suff = '-mpi'

        # run make script
        cmd = "./make%s -I%s,%s -L%s" % (suff, meepinc, numpyinc, meeplib)
        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """
        Install by unpacking tarball in dist directory,
        and copying site-packages dir to installdir.
        """

        # locate tarball
        tarball = None
        shortver = '.'.join(self.version().split('.')[0:2])
        fn_pattern = os.path.join(self.getcfg('startfrom'),
                                  'dist',
                                  "%s-%s.*.tar.gz" % (self.name(), shortver))
        matches = glob.glob(fn_pattern)
        if not matches:
            self.log.error("No tarball found at %s" % fn_pattern)
        elif len(matches) > 1:
            self.log.error("Multiple matches found for tarball: %s" % matches)
        else:
            tarball = matches[0]
            self.log.info("Tarball found at %s" % tarball)

        # unpack tarball to temporary directory
        tmpdir = tempfile.mkdtemp()
        srcdir = unpack(tarball, tmpdir)
        if not srcdir:
            self.log.error("Unpacking tarball %s failed?" % tarball)

        # locate site-packages dir to copy by diving into unpacked tarball
        src = srcdir
        while len(os.listdir(src)) == 1:
            src = os.path.join(src, os.listdir(src)[0])
        if not os.path.basename(src) =='site-packages':
            self.log.error("Expected to find a site-packages path, but found something else: %s" % src)

        # copy contents of site-packages dir
        dest = os.path.join(self.installdir, 'site-packages')
        try:
            shutil.copytree(src, dest)
            shutil.rmtree(tmpdir)
        except OSError, err:
            self.log.exception("Failed to copy directory %s to %s: %s" % (src, dest, err))

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths',{'files':["site-packages/meep_mpi.py"],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

    def make_module_extra(self):
        """Set python-meep specific environment variables in module."""

        txt = Application.make_module_extra(self)

        meep = os.getenv("SOFTROOTMEEP")

        txt += "setenv\tMEEP_INCLUDE\t\t%s/include\n" % meep
        txt += "setenv\tMEEP_LIB\t\t%s/lib\n" % meep

        for var in ["PYTHONMEEPPATH", "PYTHONMEEP_INCLUDE", "PYTHONPATH"]:
            txt += "setenv\t%s\t\t$root/site-packages\n" % var

        return txt