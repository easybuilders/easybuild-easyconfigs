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
EasyBuild support for python-meep, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import glob
import os
import shutil
import tempfile

from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import extract_file, rmtree2
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_python_minus_meep(PythonPackage):
    """
    Support for building and installing python-meep
    """

    def configure_step(self):
        """Just check whether dependencies (Meep, Python) are available."""

        # make sure that required dependencies are loaded
        deps = ["Meep", "Python"]
        for dep in deps:
            if not get_software_root(dep):
                raise EasyBuildError("Module for %s not loaded.", dep)
        super(EB_python_minus_meep, self).configure_step()

    def build_step(self):
        """Build python-meep using available make/make-mpi script."""

        # determine make script arguments
        meep = get_software_root('Meep')
        meepinc = os.path.join(meep, 'include')
        meeplib = os.path.join(meep, 'lib')
        numpyinc = os.path.join(get_software_root('Python'), self.pylibdir, 'numpy', 'core', 'include')

        # determine suffix for make script
        suff = ''
        if self.toolchain.options.get('usempi', None):
            suff = '-mpi'

        # run make script
        cmd = "./make%s -I%s,%s -L%s" % (suff, meepinc, numpyinc, meeplib)
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """
        Install by unpacking tarball in dist directory,
        and copying site-packages dir to installdir.
        """

        # locate tarball
        tarball = None
        shortver = '.'.join(self.version.split('.')[0:2])
        fn_pattern = os.path.join(self.cfg['start_dir'],
                                  'dist',
                                  "%s-%s.*.tar.gz" % (self.name, shortver))
        matches = glob.glob(fn_pattern)
        if not matches:
            raise EasyBuildError("No tarball found at %s", fn_pattern)
        elif len(matches) > 1:
            raise EasyBuildError("Multiple matches found for tarball: %s", matches)
        else:
            tarball = matches[0]
            self.log.info("Tarball found at %s" % tarball)

        # unpack tarball to temporary directory
        tmpdir = tempfile.mkdtemp()
        srcdir = extract_file(tarball, tmpdir)
        if not srcdir:
            raise EasyBuildError("Unpacking tarball %s failed?", tarball)

        # locate site-packages dir to copy by diving into unpacked tarball
        src = srcdir
        while len(os.listdir(src)) == 1:
            src = os.path.join(src, os.listdir(src)[0])
        if not os.path.basename(src) =='site-packages':
            raise EasyBuildError("Expected to find a site-packages path, but found something else: %s", src)

        # copy contents of site-packages dir
        dest = os.path.join(self.installdir, 'site-packages')
        try:
            shutil.copytree(src, dest)
            rmtree2(tmpdir)
            os.chdir(self.installdir)
        except OSError, err:
            raise EasyBuildError("Failed to copy directory %s to %s: %s", src, dest, err)

    def sanity_check_step(self):

        custom_paths = {
                        'files':["site-packages/meep_mpi.py"],
                        'dirs':[]
                       }

        self.options['modulename'] = 'meep_mpi'

        return super(EB_python_minus_meep, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Set python-meep specific environment variables in module."""

        txt = super(EB_python_minus_meep, self).make_module_extra()

        meep = get_software_root('Meep')
        if meep is not None:
            txt += self.module_generator.set_environment('MEEP_INCLUDE', os.path.join(meep, 'include'))
            txt += self.module_generator.set_environment('MEEP_LIB', os.path.join(meep, 'lib'))

        for var in ["PYTHONMEEPPATH", "PYTHONMEEP_INCLUDE", "PYTHONPATH"]:
            txt += self.module_generator.set_environment(var, os.path.join(self.installdir, 'site-packages'))

        return txt
