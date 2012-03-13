import os, re
from distutils.version import LooseVersion

    
def get_git_revision():
    try:
        import git
        path = os.path.dirname(__file__)
        g = git.Git(path)
        return g.rev_list("HEAD").splitlines()[0]
    except:
        return VERSION
    

VERSION = LooseVersion("1.0")
VERBOSE_VERSION = LooseVersion("%s-r%s" % (VERSION, get_git_revision()))
