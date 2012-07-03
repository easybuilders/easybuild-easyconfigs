##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman, Toon Willems
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
import os

from easybuild.tools.build_log import getLog
import easybuild.tools.config as config


log = getLog('easybuild_config')

# buildPath possibly overridden by EASYBUILDBUILDPATH
# installPath possibly overridden by EASYBUILDINSTALLPATH
buildDir = 'easybuild_build'
installDir = 'easybuild'
sourceDir = "easybuild_sources"

if os.getenv('EASYBUILDPREFIX'):
    prefix = os.getenv('EASYBUILDPREFIX')
else:
    prefix = os.getenv('HOME')

if not prefix:
    prefix = "/tmp"

buildPath = os.path.join(prefix, buildDir)
installPath = os.path.join(prefix, installDir)
sourcePath = os.path.join(prefix, sourceDir)

# repository for eb files
## possible repository types are:
## 'fs'    : plain filesystem
##           repositoryPath = ("path/to/directory")
## 'git'   : bare git repository (created git clone --bare or git init --bare (but make sure to have at least
##           one push to it once, we can't handle empty git repos)
##           repositoryPath = ("ssh://user@server/path/to/repo.git","path/inside/repo") #not starting with '/' !
##           this requires GitPython
## 'svn'   " svn repository
##           repositoryPath = ("svn+ssh://user@server/path/to/repo/path/inside/repo")
##           this requires pysvn
repositoryType = 'fs'
repositoryPath = (os.path.join(prefix, 'easybuild_ebfiles_repo'))

# log format: (dir, filename template)
# supported in template: name, version, data, time
logFormat = ("easybuildlog", "easybuild-%(name)s-%(version)s-%(date)s.%(time)s.log")

# general cleanliness
del os, getLog, config, log, prefix, buildDir, installDir, sourceDir
