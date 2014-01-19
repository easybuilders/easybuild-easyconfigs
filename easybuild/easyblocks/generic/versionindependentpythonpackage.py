##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing a Pythonpackage independend of a python version as an easyblock.

Python installs libraries by defailt in site-packages/python-xxx/
But packages that are not dependend on the python version can be installed in a different prefix, e.g. lib
as long as we add this folder to the pythonpath.

@author: Kenneth Hoste, Jens Timmerman (Ghent University)
"""
import os
import re

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.filetools import run_cmd


class VersionIndependentPythonPackage(PythonPackage):
    """Support for building/installing python packages without requiring a specific python package."""

    def build_step(self):
        """No build procedure."""
        pass

    def prepare_step(self):
        """Set pylibdir"""
        self.pylibdir = 'lib'
        super(VersionIndependentPythonPackage, self).prepare_step()

    def install_step(self):
        """Custom install procedure to skip selection of python package versions."""
        full_pylibdir = os.path.join(self.installdir, self.pylibdir)

        env.setvar('PYTHONPATH', '%s:%s' % (full_pylibdir, os.getenv('PYTHONPATH')))

        try:
            os.mkdir(full_pylibdir)
        except OSError, err:
            # this will raise an error and not return
            self.log.error("Failed to install: %s" % err)

        args = "--prefix=%s --install-lib=%s " % (self.installdir, full_pylibdir)
        args += "--single-version-externally-managed --record %s --no-compile" % os.path.join(self.builddir, 'record')
        cmd = "python setup.py install %s" % args
        run_cmd(cmd, log_all=True, simple=True, log_output=True)

        # setuptools stubbornly replaces the shebang line in scripts with
        # the full path to the Python interpreter used to install;
        # we change it (back) to '#!/usr/bin/env python' here
        shebang_re = re.compile("^#!/.*python")
        bindir = os.path.join(self.installdir, 'bin')
        if os.path.exists(bindir):
            for script in os.listdir(bindir):
                script = os.path.join(bindir, script)
                if os.path.isfile(script):
                    try:
                        txt = open(script, 'r').read()
                        if shebang_re.search(txt):
                            new_shebang = "#!/usr/bin/env python"
                            self.log.debug("Patching shebang header line in %s to '%s'" % (script, new_shebang))
                            txt = shebang_re.sub(new_shebang, txt)
                            open(script, 'w').write(txt)
                    except IOError, err:
                        self.log.error("Failed to patch shebang header line in %s: %s" % (script, err))
