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
EasyBuild support for wxPython, implemented as an easyblock

@author: Balazs Hajgato (Vrije Universiteit Brussel)
@author: Kenneth Hoste (HPC-UGent)
"""

import os
import re

from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_wxPython(PythonPackage):
    """Support for installing the wxPython Python package."""

    def build_step(self):
        """No separate build step for wxPython."""
        pass

    def install_step(self):
        """Custom install procedure for wxPython, using provided build-wxpython.py script."""
        # wxPython configure, build, and install with one script
        script = os.path.join('wxPython', 'build-wxpython.py')
        cmd = "{0} {1} --prefix={2} --wxpy_installdir={2} --install".format(self.python_cmd, script, self.installdir)
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for wxPython."""
        majver = '.'.join(self.version.split('.')[:2])
        shlib_ext = get_shared_lib_ext()
        py_bins = ['alacarte', 'alamode', 'crust', 'shell', 'wrap', 'wxrc']
        custom_paths = {
            'files': ['bin/wxrc'] + [os.path.join('bin', 'py%s' % x) for x in py_bins] +
                     [os.path.join('lib/lib%s-%s.%s' % (x, majver, shlib_ext)) for x in ['wx_baseu', 'wx_gtk2u_core']],
            'dirs': ['include', 'share', self.pylibdir],
        }

        # test using 'import wx'
        self.options['modulename'] = 'wx'

        super(EB_wxPython, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom update for $PYTHONPATH for wxPython."""
        txt = super(EB_wxPython, self).make_module_extra()

        # make sure that correct subdir is included in update to $PYTHONPATH
        majver = '.'.join(self.version.split('.')[:2])
        txt = re.sub(self.pylibdir, os.path.join(self.pylibdir, 'wx-%s-gtk2' % majver), txt)

        return txt
