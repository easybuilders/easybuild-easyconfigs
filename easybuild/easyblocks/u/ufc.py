# Copyright 2012 Kenneth Hoste
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
EasyBuild support for UFC, implemented as an easyblock
"""
from distutils.version import LooseVersion

from easybuild.easyblocks.cmakepythonpackage import EB_CMakePythonPackage
from easybuild.tools.modules import get_software_root, get_software_version


class EB_UFC(EB_CMakePythonPackage):
    """Support for building UFC."""

    def configure(self):
        """Set some extra environment variables before configuring."""

        # make sure that required dependencies are loaded
        deps = ['Boost', 'Python', 'SWIG']
        depsdict = {}
        for dep in deps:
            deproot = get_software_root(dep)
            if not deproot:
                self.log.error("%s module not loaded?" % dep)
            else:
                depsdict.update({dep:deproot})

        # SWIG version more recent than 2.0.4 have a regression
        # which causes problems with e.g. DOLFIN if UFC was built with it
        # fixed in 2.0.7? see https://bugs.launchpad.net/dolfin/+bug/996398
        if LooseVersion(get_software_version('SWIG')) > '2.0.4':
            self.log.error("Using bad version of SWIG, expecting swig <= 2.0.4." \
                           " See https://bugs.launchpad.net/dolfin/+bug/996398")

        self.pyver = ".".join(get_software_version('Python').split(".")[:-1])

        self.updatecfg('configopts', "-DBoost_DIR=%s" % depsdict['Boost'])
        self.updatecfg('configopts', "-DBOOST_INCLUDEDIR=%s/include" % depsdict['Boost'])
        self.updatecfg('configopts', "-DBoost_DEBUG=ON -DBOOST_ROOT=%s" % depsdict['Boost'])

        self.updatecfg('configopts', '-DUFC_ENABLE_PYTHON:BOOL=ON')
        self.updatecfg('configopts', '-DSWIG_FOUND:BOOL=ON')
        self.updatecfg('configopts', '-DPYTHON_LIBRARY=%s/lib/libpython%s.so' % (depsdict['Python'],
                                                                                 self.pyver))
        self.updatecfg('configopts', '-DPYTHON_INCLUDE_PATH=%s/include/python%s' % (depsdict['Python'],
                                                                                    self.pyver))

        EB_CMakePythonPackage.configure(self)

    def sanitycheck(self):
        """Custom sanity check for UFC."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files': ['include/ufc.h'],
                                             'dirs':['lib/python%s/site-packages/ufc_utils/' % self.pyver]
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        EB_CMakePythonPackage.sanitycheck(self)
