##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild logger and log utilities, including our own EasybuildError class.
"""

import logging
import os
import sys
import time
from socket import gethostname
from copy import copy

import easybuild

# EasyBuild message prefix
EB_MSG_PREFIX = "=="


class EasyBuildError(Exception):
    """
    EasyBuildError is thrown when EasyBuild runs into something horribly wrong.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


class EasyBuildLog(logging.Logger):
    """
    The EasyBuild logger, with its own error and exception functions.
    """

    # self.raiseError can be set to False disable raising the exception which is
    # necessary because logging.Logger.exception calls self.error
    raiseError = True

    def callerInfo(self):
        (filepath, line, function_name) = self.findCaller()
        filepath_dirs = filepath.split(os.path.sep)

        for dirName in copy(filepath_dirs):
            if dirName != "easybuild":
                filepath_dirs.remove(dirName)
            else:
                break
        return "(at %s:%s in %s)" % (os.path.sep.join(filepath_dirs), line, function_name)

    def error(self, msg, *args, **kwargs):
        newMsg = "EasyBuild crashed with an error %s: %s" % (self.callerInfo(), msg)
        logging.Logger.error(self, newMsg, *args, **kwargs)
        if self.raiseError:
            raise EasyBuildError(newMsg)

    def exception(self, msg, *args):
        ## don't raise the exception from within error
        newMsg = "EasyBuild encountered an exception %s: %s" % (self.callerInfo(), msg)

        self.raiseError = False
        logging.Logger.exception(self, newMsg, *args)
        self.raiseError = True

        raise EasyBuildError(newMsg)


# set format for logger
logging_format = EB_MSG_PREFIX + ' %(asctime)s %(name)s %(levelname)s %(message)s'
formatter = logging.Formatter(logging_format)

# redirect standard handler of root logger to /dev/null
# without this, everything is logged twice (one by root logger, once by descendant logger)
logging.basicConfig(level=logging.ERROR, format=logging_format, filename='/dev/null')

logging.setLoggerClass(EasyBuildLog)

def getLog(name=None):
    """
    Generate logger object
    """
    log = logging.getLogger(name)
    log.info("Logger started for %s." % name)
    return log

def removeLogHandler(hnd):
    """
    Remove handler from root log
    """
    log = logging.getLogger()
    log.removeHandler(hnd)

def initLogger(name=None, version=None, debug=False, filename=None, typ='UNKNOWN'):
    """
    Return filename of the log file being written
    - does not append
    - sets log handlers
    """

    # obtain root logger
    log = logging.getLogger()

    # determine log level
    if debug:
        defaultLogLevel = logging.DEBUG
    else:
        defaultLogLevel = logging.INFO

    # set log level for root logger
    log.setLevel(defaultLogLevel)

    if (name and version) or filename:
        if not filename:
            filename = logFilename(name, version)
        hand = logging.FileHandler(filename)
    else:
        hand = logging.StreamHandler(sys.stdout)

    hand.setFormatter(formatter)
    log.addHandler(hand)

    # initialize our logger
    log = logging.getLogger(typ)
    log.setLevel(defaultLogLevel)

    ## init message
    log.info("Log initialized with name %s version %s to file %s on host %s" % (name,
                                                                                version,
                                                                                filename,
                                                                                gethostname()
                                                                                ))
    log.info("This is EasyBuild %s" % easybuild.VERBOSE_VERSION)

    return filename, log, hand

def logFilename(name, version):
    """
    Generate a filename to be used
    """
    # this can't be imported at the top, otherwise we'd have a cyclic dependency
    from easybuild.tools.config import logFormat, get_build_log_path

    date = time.strftime("%Y%m%d")
    timeStamp = time.strftime("%H%M%S")

    filename = os.path.join(get_build_log_path(), logFormat() % {'name':name,
                                                                 'version':version,
                                                                 'date':date,
                                                                 'time':timeStamp
                                                                 })

    # Append numbers if the log file already exist
    counter = 1
    while os.path.isfile(filename):
        counter += 1
        filename = "%s.%d" % (filename, counter)

    return filename

def print_msg(msg, log=None):
    """
    Print a message to stdout.
    """
    if log:
        log.info(msg)
    print "%s %s" % (EB_MSG_PREFIX, msg)

if __name__ == '__main__':
    initLogger('test', '1.0.0')
    fn, testlog, _ = initLogger(typ='build_log')
    testlog.info('Testing buildLog...')
    "Tested buildLog, see %s" % fn
