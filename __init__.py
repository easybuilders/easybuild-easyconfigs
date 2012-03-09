import os
from distutils.version import LooseVersion

VERSION = LooseVersion("0.5")

def get_svn_revision(path=None):
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
    entries_path = '%s/.svn/entries' % path

    try:
        entries = open(entries_path, 'r').read()
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
            dom = minidom.parse(entries_path)
            rev = dom.getElementsByTagName('entry')[0].getAttribute('revision')

    if rev:
        return rev


def get_git_revision():
    """
    Returns the git revision (e.g. aab4afc016b742c6d4b157427e192942d0e131fe),
    or UNKNOWN is getting the git revision fails
    """
    try:
        import git
        path = os.path.dirname(__file__)
        g = git.Git(path)
        return g.rev_list("HEAD").splitlines()[0]
    except (ImportError, git.GitCommandError):
        return "UNKNOWN"

VERBOSE_VERSION = LooseVersion("%s-r%s" % (VERSION, get_git_revision()))
