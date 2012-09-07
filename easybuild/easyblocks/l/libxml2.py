##
# Copyright 2012 Jens Timmerman
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
EasyBuild support for building and installing libxml2 with python bindings,
implemented as an easyblock.
"""
import os

from easybuild.framework.application import Application
from easybuild.easyblocks.pythonpackage import EB_PythonPackage

class EB_libxml2(Application, EB_PythonPackage):
    """Support for building and installing libxml2 with python bindings"""
    def __init__(self, *args, **kwargs):
	"""
	Constructor
	init as a pythonpackage, since that is also an application
	"""
	EB_PythonPackage.__init__(self, *args, **kwargs)

    def configure(self):
        """
        Configure and 
        Test if python module is loaded
        """
        if not os.getenv("EBROOTPYTHON"):
            self.log.error("Python module not loaded")
        Application.configure(self)
	os.chdir('python')
        EB_PythonPackage.configure(self)
	os.chdir('..')

    def make(self):
        """
        Make libxml2 first, then make python bindings
        """
        Application.make(self)
        os.chdir('python')
        # set cflags to point to include folder 
        os.putenv('CFLAGS', "-I../include")
        EB_PythonPackage.make(self)
	os.chdir('..')

    def make_install(self):
        """
        Install libxml2 and install python bindings
        """
        Application.make_install(self)
	os.chdir('python')
        EB_PythonPackage.make_install(self)
	os.chdir('..')

    def make_module_extra(self):
	"""
	Add python bindings to the pythonpath
	"""
	return EB_PythonPackage.make_module_extra(self)

#    def sanitycheck(self):
#        """Custom sanity check for Pasha"""
#        self.setcfg('sanityCheckPaths', {
#                                         'files':["bin/pasha-%s" % x for x in ["kmergen",
#                                                                               "pregraph",
#                                                                               "graph"]],
#                                        'dirs':[""],
#                                        })

