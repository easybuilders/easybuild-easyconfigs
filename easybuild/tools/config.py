"""
EasyBuild configuration (paths etc.)
"""

import os
from easybuild.tools.buildLog import getLog

log = getLog('config')

variables = {}
requiredVariables = ['buildPath', 'installPath', 'sourcePath', 'logFormat']
environmentVariables = {
    'buildPath': 'EASYBUILDBUILDPATH',
    'installPath': 'EASYBUILDTESTINSTALLPATH'
}

def init(filename, **kwargs):
    """
    Gather all variables and check if they're valid
    Variables are read in this order of preference: CLI option > environment > config-file
    """

    variables.update(readConfiguration(filename)) # Config-file
    variables.update(readEnvironment(environmentVariables)) # Environment
    variables.update(kwargs) # CLI options

    for key in requiredVariables:
        if not variables.has_key(key):
            log.error('Cannot determine value for configuration variable %s. ' \
                      'Please specify it in your configfile %s.' % (key, filename))
            continue

        # Verify directories
        value = variables[key]
        if (key in ['buildPath', 'installPath'] and not os.path.isdir(value)) or (key in ['sourcePath'] and type(value) == str and not os.path.isdir(value)):
            log.warn('The %s directory %s does not exist or does not have proper permissions' % (key, value))
            continue
        if key in ['sourcePath'] and type(value) == list:
            for d in value:
                if not os.path.isdir(d):
                    log.warn('The %s directory %s does not exist or does not have proper permissions' % (key, d))
                    continue

def readConfiguration(filename):
    """
    Read variables from the configfile
    """
    fileVariables = {}
    try:
        execfile(filename, {}, fileVariables)
    except Exception, err:
        log.exception("Failed to read configfile %s %s" % (filename, err))
    return fileVariables

def readEnvironment(environmentVariables, strict=False):
    """
    Read variables from the environment
    """
    result = {}
    for key in environmentVariables.keys():
        environmentKey = environmentVariables[key]
        if os.environ.has_key(environmentKey):
            result[key] = os.environ[environmentKey]
        elif strict:
            log.error("Can't determine value for %s. Environment variable %s is missing" % (key, environmentKey))
    return result

def buildPath():
    """
    Return the buildpath
    """
    return variables['buildPath']

def sourcePath():
    """
    Return the sourcepath
    """
    return variables['sourcePath']

def installPath(typ=None):
    """
    Returns the installpath, convention is
    - /apps/site/cluster/name/version
    """
    if typ and typ == 'mod':
        suffix = 'modules'
    else:
        suffix = 'software'
    return os.path.join(variables['installPath'], suffix)

def repositoryType():
    """
    Return the source-control path
    """
    return variables['repositoryType']

def repositoryPath():
    """
    Return the source-control path
    """
    return variables['repositoryPath']

def logFormat():
    """
    Return the logformat
    """
    return variables['logFormat'][1]

def logPath():
    """
    Return the logpath
    """
    return variables['logFormat'][0]
