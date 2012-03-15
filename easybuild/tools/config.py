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
"""
EasyBuild configuration (paths, preferences, etc.)
"""
import os

from easybuild.tools.build_log import getLog

log = getLog('config')

variables = {}
requiredVariables = ['buildPath', 'installPath', 'sourcePath', 'logFormat', 'repositoryType', 'repositoryPath']
environmentVariables = {
    'buildPath': 'EASYBUILDBUILDPATH',
    'installPath': 'EASYBUILDINSTALLPATH'
}

def init(filename, **kwargs):
    """
    Gather all variables and check if they're valid
    Variables are read in this order of preference: CLI option > environment > config file
    """

    variables.update(readConfiguration(filename)) # config file
    variables.update(readEnvironment(environmentVariables)) # environment
    variables.update(kwargs) # CLI options

    for key in requiredVariables:
        if not key in variables:
            log.error('Cannot determine value for configuration variable %s. ' \
                      'Please specify it in your config file %s.' % (key, filename))
            continue

        # verify directories, warn if they don't exist
        value = variables[key]
        dirNotFound = key in ['buildPath', 'installPath'] and not os.path.isdir(value)
        srcDirNotFound = key in ['sourcePath'] and type(value) == str and not os.path.isdir(value)
        if dirNotFound or srcDirNotFound:
            log.warn('The %s directory %s does not exist or does not have proper permissions' % (key, value))
            continue
        if key in ['sourcePath'] and type(value) == list:
            for d in value:
                if not os.path.isdir(d):
                    log.warn('The %s directory %s does not exist or does not have proper permissions' % (key, d))
                    continue

    if variables['repositoryType'] == 'fs' and not os.path.isdir(variables['repositoryPath']):
        strs = ('repositoryPath', variables['repositoryPath'])
        log.warn('The %s directory %s does not exist or does not have proper permissions' % strs)

def readConfiguration(filename):
    """
    Read variables from the config file
    """
    fileVariables = {}
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

def sourcePath():
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

def repositoryType():
    """
    Return the repository type (e.g. fs, git, svn)
    """
    return variables['repositoryType']

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
