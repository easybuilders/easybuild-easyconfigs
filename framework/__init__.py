#Copyright 2009-2012 Dries Verdegem, Jens Timmerman, Kenneth Hoste, Pieter De Baets, Stijn De Weirdt
#
#This file is part of easybuild.
#
#Easybuild is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation v2.
#
#Easybuild is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with Easybuild.  If not, see <http://www.gnu.org/licenses/>.

import os
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
