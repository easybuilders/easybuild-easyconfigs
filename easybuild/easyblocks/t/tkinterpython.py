##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for building and installing Tkinter. This is the Python core
module to use Tcl/Tk.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Adam Huffman (The Francis Crick Institute)
@author: Ward Poelmans (Free University of Brussels)
"""
import glob
import os
import shutil
from distutils.version import LooseVersion

from easybuild.easyblocks.p.python import EB_Python
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import copy, mkdir, rmtree2
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_TkinterPython(EB_Python):
    """Support for building/installing the Python Tkinter module
    based on the normal Python module. We build a normal python
    but only install the Tkinter bits.
    """

    def configure_step(self):
        """Check for Tk"""
        tk = get_software_root('Tk')
        if not tk:
            raise EasyBuildError("Tk is mandatory to build Tkinter")

        super(EB_TkinterPython, self).configure_step()

    def install_step(self):
        """Install python but only keep the bits we need"""
        super(EB_TkinterPython, self).install_step()

        tmpname = "eb-tmp"
        tmpdir = os.path.join(self.installdir, tmpname)
        mkdir(tmpdir)

        pyver = '.'.join(self.version.split('.')[:2])
        libdir = os.path.join(self.installdir, "lib", "python%s" % pyver)
        tkdirs = ["lib-tk", "lib-dynload/_tkinter.so"]

        copy([os.path.join(libdir, x) for x in tkdirs], tmpdir)

        delete_dirs = [x for x in os.listdir(self.installdir) if not x == tmpname]

        for deldir in delete_dirs:
            rmtree2(os.path.join(self.installdir, deldir))

        mkdir(libdir, parents=True)
        shutil.move(os.path.join(tmpdir, tkdirs[0]), libdir)
        shutil.move(os.path.join(tmpdir, os.path.basename(tkdirs[1])), libdir)

        rmtree2(tmpdir)

    def sanity_check_step(self):
        """Custom sanity check for Python."""
        if LooseVersion(self.version) >= LooseVersion('3'):
            tkinter = 'tkinter'
        else:
            tkinter = 'Tkinter'
        custom_commands = ["python -c 'import %s'" % tkinter]

        pyver = 'python' + '.'.join(self.version.split('.')[:2])
        shlib_ext = get_shared_lib_ext()

        # check whether _tkinter*.so is found, exact filename doesn't matter
        tkinter_so = os.path.join(self.installdir, 'lib', pyver, '_tkinter*.' + shlib_ext)
        tkinter_so_hits = glob.glob(tkinter_so)
        if len(tkinter_so_hits) == 1:
            self.log.info("Found exactly one _tkinter*.so: %s", tkinter_so_hits[0])
        else:
            raise EasyBuildError("Expected to find exactly one _tkinter*.so: %s", tkinter_so_hits)

        custom_paths = {
            'files': [],
            'dirs': ['lib']
        }

        super(EB_Python, self).sanity_check_step(custom_commands=custom_commands, custom_paths=custom_paths)

    def make_module_extra(self):
        """Set PYTHONPATH"""
        txt = super(EB_TkinterPython, self).make_module_extra()
        pyver = '.'.join(self.version.split('.')[:2])
        txt += self.module_generator.prepend_paths('PYTHONPATH', os.path.join("lib", "python%s" % pyver))

        return txt
