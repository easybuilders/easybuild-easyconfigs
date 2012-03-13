##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
from distutils.version import LooseVersion
import os

VERSION = LooseVersion("0.5")

def getSvnRevision(path=None):
    """
    Returns the SVN revision in the form ABCD,
    where ABCD is the revision number.

    Returns SVN-unknown if anything goes wrong, such as an unexpected
    format of internal SVN files.

    If path is provided, it should be a directory whose SVN info you want to
    inspect. If it's not provided, this will use the root django/ package
    directory.

    Source: https://code.djangoproject.com/browser/django/trunk/django/utils/version.py
    License: BSD
    """
    import re
    rev = None
    if path is None:
        path = os.path.dirname(__file__)
    entriesPath = '%s/.svn/entries' % path

    try:
        entries = open(entriesPath, 'r').read()
    except IOError:
        pass
    else:
        # Versions >= 7 of the entries file are flat text.  The first line is
        # the version number. The next set of digits after 'dir' is the revision.
        if re.match('(\d+)', entries):
            rev_match = re.search('\d+\s+dir\s+(\d+)', entries)
            if rev_match:
                rev = rev_match.groups()[0]
        # Older XML versions of the file specify revision as an attribute of
        # the first entries node.
        else:
            from xml.dom import minidom
            dom = minidom.parse(entriesPath)
            rev = dom.getElementsByTagName('entry')[0].getAttribute('revision')

    if rev:
        return rev


def getGitRevision():
    """
    Returns the git revision (e.g. aab4afc016b742c6d4b157427e192942d0e131fe),
    or UNKNOWN is getting the git revision fails

    relies on GitPython (see http://gitorious.org/git-python)
    """
    try:
        import git
        path = os.path.dirname(__file__)
        g = git.Git(path)
        return g.rev_list("HEAD").splitlines()[0]
    except (ImportError, git.GitCommandError):
        return "UNKNOWN"

VERBOSE_VERSION = LooseVersion("%s-r%s" % (VERSION, getGitRevision()))
