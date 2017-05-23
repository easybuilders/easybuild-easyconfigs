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

@author: Adam Huffman (The Francis Crick Institute)
@author: Ward Poelmans (Free University of Brussels)
"""
import os
import shutil
import tempfile
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.pythonpackage import det_pylibdir
from easybuild.easyblocks.python import EB_Python
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import copy, mkdir, rmtree2
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_Tkinter(EB_Python):
    """Support for building/installing the Python Tkinter module
    based on the normal Python module. We build a normal python
    but only install the Tkinter bits.
    """

    def configure_step(self):
        """Check for Tk before configuring"""
        tk = get_software_root('Tk')
        if not tk:
            raise EasyBuildError("Tk is mandatory to build Tkinter")

        super(EB_Tkinter, self).configure_step()

    def install_step(self):
        """Install python but only keep the bits we need"""
        super(EB_Tkinter, self).install_step()

        tmpdir = tempfile.mkdtemp(dir=self.builddir)

        pylibdir = os.path.join(self.installdir, os.path.dirname(det_pylibdir()))
        tkparts = ["lib-tk", "lib-dynload/_tkinter.so"]

        copy([os.path.join(pylibdir, x) for x in tkparts], tmpdir)

        rmtree2(self.installdir)

        mkdir(pylibdir, parents=True)
        try:
            shutil.move(os.path.join(tmpdir, tkparts[0]), pylibdir)
            shutil.move(os.path.join(tmpdir, os.path.basename(tkparts[1])), pylibdir)
        except (IOError, OSError) as err:
            raise EasyBuildError("Failed to move Tkinter back to the install directory: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for Python."""
        if LooseVersion(self.version) >= LooseVersion('3'):
            tkinter = 'tkinter'
        else:
            tkinter = 'Tkinter'
        custom_commands = ["python -c 'import %s'" % tkinter]

        shlib_ext = get_shared_lib_ext()
        pylibdir = os.path.dirname(det_pylibdir())

        custom_paths = {
            'files': ['%s/_tkinter.%s' % (pylibdir, shlib_ext)],
            'dirs': ['lib']
        }
        super(EB_Python, self).sanity_check_step(custom_commands=custom_commands, custom_paths=custom_paths)

    def make_module_extra(self):
        """Set PYTHONPATH"""
        txt = super(EB_Tkinter, self).make_module_extra()
        pylibdir = os.path.dirname(det_pylibdir())
        txt += self.module_generator.prepend_paths('PYTHONPATH', pylibdir)

        return txt
