import os

from easybuild.tools.buildLog import getLog
import easybuild.tools.config as config

log = getLog('easybuild_config')

# buildPath possibly overridden by EASYBUILDBUILDPATH
# installPath possibly overridden by EASYBUILDINSTALLPATH
buildDir='easybuild_testsuite_build'
installDir='easybuild_testsuite'
sourceDir="easybuild_sources"
prefix = os.getenv('HOME')

if not prefix:
    prefix = "/tmp"

buildPath = os.path.join(prefix,buildDir)
installPath = os.path.join(prefix,installDir)
sourcePath = os.path.join(prefix,sourceDir)

# repository for eb files
## possible repository types are:
## 'fs'    : plain filesystem
##           repositoryPath = ("path/to/directory")
## 'git'   : bare git repository (created git clone --bare or git init --bare (but make sure to have at least one push to it once, we can't handle empty git repos)
##           repositoryPath = ("ssh://user@server/path/to/repo.git","path/inside/repo") #not starting with '/' !
##           this requires GitPython
## 'svn'   " svn repository
##           repositoryPath = ("svn+ssh://user@server/path/to/repo/path/inside/repo")
##           this requires pysvn
repositoryType = 'fs'
repositoryPath = (os.path.join(prefix,'easybuild_testsuite_ebFiles_repo'))

# log format: (dir, filename template)
# supported in template: name, version, data, time
logFormat = ("easybuildlog", "easybuild-%(name)s-%(version)s-%(date)s.%(time)s.log")

# general cleanliness
del os, getLog, config, log, prefix, buildDir, installDir, sourceDir
