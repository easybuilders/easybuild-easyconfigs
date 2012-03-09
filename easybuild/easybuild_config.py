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
repositoryType = 'fs'
repositoryPath = (os.path.join(prefix,'easybuild_testsuite_ebFiles_repo'))

# log format: (dir, filename template)
# supported in template: name, version, data, time
logFormat = ("easybuildlog", "easybuild-%(name)s-%(version)s-%(date)s.%(time)s.log")

# general cleanliness
del os, getLog, config, log, prefix, buildDir, installDir, sourceDir
