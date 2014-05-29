# #
# Copyright 2009-2014 Ghent University
# Copyright 2009-2014 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2014 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2014 Jens Timmerman
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
import os
from distutils.version import LooseVersion
from pkgutil import extend_path

# note: release candidates should be versioned as a pre-release, e.g. "1.1rc1"
# 1.1-rc1 would indicate a post-release, i.e., and update of 1.1, so beware
VERSION = LooseVersion("1.13.0")
UNKNOWN = "UNKNOWN"


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
    VERBOSE_VERSION = LooseVersion("%s-r%s" % (VERSION, get_git_revision()))

# Extend path so python finds our easyblocks in the subdirectories where they are located
subdirs = [chr(l) for l in range(ord('a'), ord('z') + 1)] + ['0']
__path__.extend([os.path.join(__path__[0], subdir) for subdir in subdirs])
# And let python know this is not the only place to look for them, so we can have multiple
# easybuild/easyblock paths in your python search path, next to the official easyblocks distribution
__path__ = extend_path(__path__, __name__)  # @ReservedAssignment

del subdir, subdirs, l, git_rev
