# #
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
# #
"""
EasyBuild support for installing EasyBuild, implemented as an easyblock

@author: Kenneth Hoste (UGent)
"""
import copy
import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.tools.modules import get_software_root_env_var_name
from easybuild.tools.ordereddict import OrderedDict
from easybuild.tools.utilities import flatten


# note: we can't use EB_EasyBuild as easyblock name, as that would require an easyblock named 'easybuild.py',
#       which would screw up namespacing and create all kinds of problems (e.g. easyblocks not being found anymore)
class EB_EasyBuildMeta(PythonPackage):
    """Support for install EasyBuild."""

    def __init__(self, *args, **kwargs):
        """Initialize custom class variables."""
        super(EB_EasyBuildMeta, self).__init__(*args, **kwargs)
        self.orig_orig_environ = None

    def check_readiness_step(self):
        """Make sure EasyBuild can be installed with a loaded EasyBuild module."""
        env_var_name = get_software_root_env_var_name(self.name)
        if env_var_name in os.environ:
            os.environ.pop(env_var_name)
            self.log.debug("$%s is unset so EasyBuild can be installed with a loaded EasyBuild module" % env_var_name)
        else:
            self.log.debug("Not unsetting $%s since it's not set" % env_var_name)

        super(EB_EasyBuildMeta, self).check_readiness_step()

    def build_step(self):
        """No building for EasyBuild packages."""
        pass

    def install_step(self):
        """Install EasyBuild packages one by one."""

        try:
            subdirs = os.listdir(self.builddir)
            for pkg in ['easyconfigs', 'easyblocks', 'framework']:
                seldirs = [x for x in subdirs if x.startswith('easybuild-%s-' % pkg)]
                if not len(seldirs) == 1:
                    self.log.error("Failed to find EasyBuild %s package (subdirs: %s, seldirs: %s)" % (pkg, subdirs, seldirs))

                self.log.debug("Installing EasyBuild package %s" % pkg)
                os.chdir(os.path.join(self.builddir, seldirs[0]))
                super(EB_EasyBuildMeta, self).install_step()

        except OSError, err:
            self.log.error("Failed to install EasyBuild packages: %s" % err)

    def sanity_check_step(self):
        """Custom sanity check for EasyBuild."""

        # list of dirs to check, by package
        # boolean indicates whether dir is expected to reside in Python lib/pythonX/site-packages dir
        subdirs_by_pkg = [
                          ('framework', [('easybuild/framework', True), ('easybuild/tools', True)]),
                          ('easyblocks', [('easybuild/easyblocks', True)]),
                          ('easyconfigs', [('easybuild/easyconfigs', False)]),
                         ]

        # final list of directories to check, by setup tool
        # order matters, e.g. setuptools before distutils
        eb_dirs = OrderedDict()
        eb_dirs['setuptools'] = []
        eb_dirs['distutils.core'] = flatten([x[1] for x in subdirs_by_pkg])

        # determine setup tool (setuptools or distutils)
        setup_tool = None
        for tool in eb_dirs.keys():
            self.log.debug("Trying %s.." % tool)
            try:
                exec "from %s import setup" % tool
                del setup
                setup_tool = tool
                break
            except ImportError:
                pass
        self.log.debug('setup_tool: %s' % setup_tool)

        # for a setuptools installation, we need to figure out the egg dirs since we don't know the individual package versions
        if setup_tool == 'setuptools':
            try:
                installed_dirs = os.listdir(os.path.join(self.installdir, self.pylibdir))
                for (pkg, subdirs) in subdirs_by_pkg:
                    sel_dirs = [x for x in installed_dirs if x.startswith('easybuild_%s' % pkg)]
                    if not len(sel_dirs) == 1:
                        self.log.error("Failed to isolate installed egg dir for easybuild-%s" % pkg)

                    for (subdir, _) in subdirs:
                        # eggs always go in Python lib/pythonX/site-packages dir with setuptools 
                        eb_dirs['setuptools'].append((os.path.join(sel_dirs[0], subdir), True))
            except OSError, err:
                self.log.error("Failed to determine sanity check dir paths: %s" % err)

        # set of sanity check paths to check for EasyBuild
        custom_paths = {
                        'files': ['bin/eb'],
                        'dirs': [self.pylibdir] + [[x, os.path.join(self.pylibdir, x)][y] for (x, y) in eb_dirs[setup_tool]],
                       }

        # set of sanity check commands to run for EasyBuild
        custom_commands = [
                           # this may spit out a wrong version, but that should be safe to ignore
                           # occurs when the EasyBuild being used is newer than the EasyBuild being installed
                           ('eb', '--version'),
                           ('eb', '-a'),
                           ('eb', '-e ConfigureMake -a')
                          ]

        # (temporary) cleanse copy of original environment to avoid conflict with (potentially) loaded EasyBuild module
        self.orig_orig_environ = copy.deepcopy(self.orig_environ)
        for env_var in ['_LMFILES_', 'LOADEDMODULES']:
            if env_var in self.orig_environ:
                self.orig_environ.pop(env_var)
                os.environ.pop(env_var)
                self.log.debug("Unset $%s in current env and copy of original env to make sanity check work" % env_var)

        super(EB_EasyBuildMeta, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_step(self, fake=False):
        """Create module file, before copy of original environment that was tampered with is restored."""
        modpath = super(EB_EasyBuildMeta, self).make_module_step(fake=fake)

        if not fake:
            # restore copy of original environment
            self.orig_environ = copy.deepcopy(self.orig_orig_environ)
            self.log.debug("Restored copy of original environment")

        return modpath
