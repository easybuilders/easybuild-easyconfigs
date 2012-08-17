##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
# Copyright 2012 Toon Willems
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
"""
EasyBuild configuration (paths, preferences, etc.)
"""

import os
import tempfile

from easybuild.tools.build_log import getLog
import easybuild.tools.repository as repo


log = getLog('config')

variables = {}
requiredVariables = ['buildPath', 'installPath', 'sourcePath', 'logFormat', 'repository', 'repositoryPath']
environmentVariables = {
    'buildPath': 'EASYBUILDBUILDPATH', # temporary build path
    'installPath': 'EASYBUILDINSTALLPATH', # final install path
    'logDir': 'EASYBUILDLOGDIR', # log directory where temporary log files are stored
    'configFile': 'EASYBUILDCONFIG', # path to the config file
    'testOutputPath': 'EASYBUILDTESTOUTPUT', # path to where jobs should place test output
}

def init(filename, **kwargs):
    """
    Gather all variables and check if they're valid
    Variables are read in this order of preference: CLI option > environment > config file
    """

    variables.update(readConfiguration(filename)) # config file
    variables.update(readEnvironment(environmentVariables)) # environment
    variables.update(kwargs) # CLI options

    def create_dir(dirtype, dirname):
        log.warn('Will try to create the %s directory %s.' % (dirtype, dirname))
        try:
            os.makedirs(dirname)
        except OSError, err:
            log.error("Failed to create directory %s: %s" % (dirname, err))
        log.warn("%s directory %s created" % (dirtype, dirname))

    for key in requiredVariables:
        if not key in variables:
            log.error('Cannot determine value for configuration variable %s. ' \
                      'Please specify it in your config file %s.' % (key, filename))
            continue

        # verify directories, try and create them if they don't exist
        value = variables[key]
        dirNotFound = key in ['buildPath', 'installPath'] and not os.path.isdir(value)
        srcDirNotFound = key in ['sourcePath'] and type(value) == str and not os.path.isdir(value)
        if dirNotFound or srcDirNotFound:
            log.warn('The %s directory %s does not exist or does not have proper permissions' % (key, value))
            create_dir(key, value)
            continue
        if key in ['sourcePath'] and type(value) == list:
            for d in value:
                if not os.path.isdir(d):
                    create_dir(key, d)
                    continue

    # update MODULEPATH if required
    ebmodpath = os.path.join(installPath(typ='mod'), 'all')
    modulepath = os.getenv('MODULEPATH')
    if not modulepath or not ebmodpath in modulepath:
        if modulepath:
            os.environ['MODULEPATH'] = "%s:%s" % (ebmodpath, modulepath)
        else:
            os.environ['MODULEPATH'] = ebmodpath
        log.info("Extended MODULEPATH with module install path used by EasyBuild: %s" % os.getenv('MODULEPATH'))

def readConfiguration(filename):
    """
    Read variables from the config file
    """
    fileVariables = {'FileRepository': repo.FileRepository,
                     'GitRepository': repo.GitRepository,
                     'SvnRepository': repo.SvnRepository
                    }
    try:
        execfile(filename, {}, fileVariables)
    except (IOError, SyntaxError), err:
        log.exception("Failed to read config file %s %s" % (filename, err))

    return fileVariables

def readEnvironment(envVars, strict=False):
    """
    Read variables from the environment
        - strict=True enforces that all possible environment variables are found
    """
    result = {}
    for key in envVars.keys():
        environmentKey = envVars[key]
        if environmentKey in os.environ:
            result[key] = os.environ[environmentKey]
        elif strict:
            log.error("Can't determine value for %s. Environment variable %s is missing" % (key, environmentKey))

    return result

def buildPath():
    """
    Return the build path
    """
    return variables['buildPath']

def source_path():
    """
    Return the source path
    """
    return variables['sourcePath']

def installPath(typ=None):
    """
    Returns the install path
    - subdir 'software' for actual installation (default)
    - subdir 'modules' for environment modules (typ='mod')
    """
    if typ and typ == 'mod':
        suffix = 'modules'
    else:
        suffix = 'software'

    return os.path.join(variables['installPath'], suffix)

def getRepository():
    """
    Return the repository (git, svn or file)
    """
    return variables['repository']

def repositoryPath():
    """
    Return the repository path
    """
    return variables['repositoryPath']

def logFormat():
    """
    Return the log format
    """
    if 'logFormat' in variables:
        return variables['logFormat'][1]
    else:
        return "easybuild-%(name)s-%(version)s-%(date)s.%(time)s.log"

def logPath():
    """
    Return the log path
    """
    return variables['logFormat'][0]

def get_build_log_path():
    """
    return temporary log directory
    """
    return variables.get('logDir', tempfile.gettempdir())

