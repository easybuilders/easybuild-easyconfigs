"""
Set of logging parameters
"""

import sys, os, logging
from socket import gethostname
import easybuild

class myError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class newLog(logging.Logger):
    # self.rais can be set to false disable raising the exception which is
    # necessary because logging.Logger.exception calls self.error
    rais=True

    def error(self,msg,*args,**kwargs):
        newmsg="err %s %s"%(self.findCaller(),msg)
        logging.Logger.error(self,msg,*args,**kwargs)
        if self.rais:
            raise myError(newmsg)
    
    def exception(self,msg,*args):
        ## don't raise the exception from within error
        newmsg="exc %s %s" % (self.findCaller(), msg)
        self.rais=False
        logging.Logger.exception(self, msg, *args)
        self.rais=True
        raise myError(newmsg)

fm='%(asctime)s %(name)s %(levelname)s %(message)s'
formatter=logging.Formatter(fm)

## redirect standard handler of rootlogger to /dev/null
logging.basicConfig(level=logging.ERROR, format=fm, filename='/dev/null')
logging.setLoggerClass(newLog)

def getLog(name=None):
    """
    Generate logger object
    """
    tmp = logging.getLogger(name)
    tmp.info("Logger started for %s." % name)
    return tmp

def removeLogHandler(hnd):
    """
    Remove handler from root log
    """
    log = logging.getLogger()
    log.removeHandler(hnd)

def initLogger(name=None, version=None, debug=False, filename=None, typ='UNKNOWN'):
    """
    Return filename where the logfile is being written
    - Does not append.
    - Set loghandlers
    """
    log = logging.getLogger()

    ## set loglevel
    if debug:
        defaultloglevel = logging.DEBUG
    else:
        defaultloglevel = logging.INFO

    if (name and version) or filename:
        if not filename:
            filename = logFilename(name, version)
        hand = logging.FileHandler(filename)
    else:
        hand = logging.StreamHandler(sys.stdout)
        
    hand.setFormatter(formatter)
    log.addHandler(hand)

    tmp = logging.getLogger(typ)
    tmp.setLevel(defaultloglevel)
    
    ## init message
    tmp.info("Log initialised with name %s version %s to file %s on host %s" % 
            (name, version, filename, gethostname()))
    tmp.info("This is EasyBuild %s" % easybuild.VERBOSE_VERSION) 
    return filename, tmp, hand
    
def logFilename(name, version):
    """
    Generate a filename to be used
    """
    import time
    date = time.strftime("%Y%m%d")
    time = time.strftime("%H%M%S")

    from easybuild.buildsoft.config import logFormat
    name = '/tmp/' + (logFormat() % locals())

    # Append numbers if the logfile already exist
    counter = 1
    while os.path.isfile(name):
        counter += 1
        name = "%s.%d" % (name, counter)

    return name

if __name__ == '__main__':
    initLogger('test', '1.0.0')
    fn, tmplog, hnd = initLogger(typ='buildLog')
    tmplog.info('Testing buildLog...')
    
