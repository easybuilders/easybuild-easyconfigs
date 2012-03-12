"""
EasyBuild logger and log utilities, including our own EasybuildError class.
"""

import sys, os, logging
from socket import gethostname
import easybuild

class EasyBuildError(Exception):
    """
    EasyBuildError is thrown when EasyBuild runs into something horribly wrong.
    """
    def __init__(self, msg):
        super(EasyBuildError,self).__init__(msg)
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

    def error(self,msg,*args,**kwargs):
        
        newMsg = "err %s %s"%(self.findCaller(),msg)
        logging.Logger.error(self,msg,*args,**kwargs)
        if self.raiseError:
            raise EasyBuildError(newMsg)

    def exception(self,msg,*args):
        ## don't raise the exception from within error
        newMsg="exc %s %s" % (self.findCaller(), msg)

        self.raiseError=False
        logging.Logger.exception(self, msg, *args)
        self.raiseError=True

        raise EasyBuildError(newMsg)

# set format for logger
loggingFormat='%(asctime)s %(name)s %(levelname)s %(message)s'
formatter=logging.Formatter(loggingFormat)

# redirect standard handler of root logger to /dev/null
logging.basicConfig(level=logging.ERROR, format=loggingFormat, filename='/dev/null')

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
    log = logging.getLogger()

    # set log level
    if debug:
        defaultLogLevel = logging.DEBUG
    else:
        defaultLogLevel = logging.INFO

    if (name and version) or filename:
        if not filename:
            filename = logFilename(name, version)
        hand = logging.FileHandler(filename)
    else:
        hand = logging.StreamHandler(sys.stdout)

    hand.setFormatter(formatter)
    log.addHandler(hand)

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
    import time
    date = time.strftime("%Y%m%d")
    timeStamp = time.strftime("%H%M%S")

    from easybuild.tools.config import logFormat
    filename = '/tmp/' + (logFormat() % {'name':name,
                                         'version':version,
                                         'date':date,
                                         'time':timeStamp
                                         })

    # Append numbers if the log file already exist
    counter = 1
    while os.path.isfile(filename):
        counter += 1
        filename = "%s.%d" % (filename, counter)

    return name

if __name__ == '__main__':
    initLogger('test', '1.0.0')
    fn, testlog, _ = initLogger(typ='buildLog')
    testlog.info('Testing buildLog...')
    print "Tested buildLog, see %s"%fn
