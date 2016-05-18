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
easybuild.easyblocks package declaration

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import pkg_resources
from distutils.version import LooseVersion
from pkgutil import extend_path

# note: release candidates should be versioned as a pre-release, e.g. "1.1rc1"
# 1.1-rc1 would indicate a post-release, i.e., and update of 1.1, so beware
#
# important note: dev versions should follow the 'X.Y.Z.dev0' format
# see https://www.python.org/dev/peps/pep-0440/#developmental-releases
# recent setuptools versions will *TRANSFORM* something like 'X.Y.Zdev' into 'X.Y.Z.dev0', with a warning like
#   UserWarning: Normalizing '2.4.0dev' to '2.4.0.dev0'
# This causes problems further up the dependency chain...
VERSION = LooseVersion('2.8.0')
UNKNOWN = 'UNKNOWN'


def get_git_revision():
    """
    Returns the git revision (e.g. aab4afc016b742c6d4b157427e192942d0e131fe),
    or UNKNOWN is getting the git revision fails

    relies on GitPython (see http://gitorious.org/git-python)
    """
    try:
        import git
    except ImportError:
        return UNKNOWN
    try:
        path = os.path.dirname(__file__)
        gitrepo = git.Git(path)
        return gitrepo.rev_list("HEAD").splitlines()[0]
    except git.GitCommandError:
        return UNKNOWN


git_rev = get_git_revision()
if git_rev == UNKNOWN:
    VERBOSE_VERSION = VERSION
else:
    VERBOSE_VERSION = LooseVersion("%s-r%s" % (VERSION, git_rev))

# extend path so python finds our easyblocks in the subdirectories where they are located
subdirs = [chr(l) for l in range(ord('a'), ord('z') + 1)] + ['0']
for subdir in subdirs:
    __path__ = extend_path(__path__, '%s.%s' % (__name__, subdir))

del subdir, subdirs, l, git_rev

# let python know this is not the only place to look for easyblocks, so we can have multiple
# easybuild/easyblocks paths in the Python search path, next to the official easyblocks distribution
pkg_resources.declare_namespace(__name__)
