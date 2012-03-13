"""
Modules functionality: loading modules, checking for available modules, ...
"""
import os, re, subprocess
from easybuild.tools.buildLog import getLog, initLogger, EasyBuildError
from easybuild.tools.fileTools import convertName

log = getLog('Modules')
outputMatchers = {
    # matches whitespace and module-listing headers
    'whitespace': re.compile(r"^\s*$|^(-+).*(-+)$"),
    # matches errors such as "cmdTrace.c(713):ERROR:104: 'asdfasdf' is an unrecognized subcommand"
    'error': re.compile(r"^\S+:(?P<level>\w+):(?P<code>\d+):\s+(?P<msg>.*)$"),
    # matches modules such as "... ictce/3.2.1.015.u4(default) ..."
    'available': re.compile(r"\b(?P<name>\S+?)/(?P<version>[^\(\s]+)(?P<default>\(default\))?(?:\s|$)")
}

class Modules:
    """
    Interact with modules.
    """
    def __init__(self,modulePath=None):
        self.modulePath=modulePath
        self.modules=[]
        
        self.checkModulePath()        
        
    def checkModulePath(self):
        """
        Check if MODULEPATH is set and change it if necessary.
        """
        if not os.environ.has_key('MODULEPATH'):
            log.error('MODULEPATH not found in environment')
        
        if self.modulePath:
            ## set the module path environment accordingly
            os.environ['MODULEPATH'] = ":".join(self.modulePath)
        else:
            ## take module path from environment
            self.modulePath = os.environ['MODULEPATH'].split(':')
        
        if not os.environ.has_key('LOADEDMODULES'):
            os.environ['LOADEDMODULES'] = ''

    def available(self, name=None, version=None, modulePath=None):
        """
        Return list of available modules.
        """
        if not name: name=''
        if not version: version=''

        txt = name
        if version:
            txt = "%s/%s" % (name,version)
        
        modules = self.runModule('available', txt, modulePath = modulePath)

        ## sort the answers in [name,version] pairs
        ## alphabetical order, default last
        modules.sort(key=lambda m: (m['name'] + (m['default'] or ''), m['version']))
        ans = [(mod['name'], mod['version']) for mod in modules]

        log.debug("module available name '%s' version '%s' in %s gave %d answers: %s" % 
            (name, version, modulePath, len(ans), ans))
        return ans
    
    def exists(self, name, version, modulePath=None):
        """
        Check if module is available.
        """
        return (name, version) in self.available(name, version, modulePath)
    
    def addModule(self, modules):
        """
        Check if module exist, if so add to list.
        """
        for mod in modules:
            if type(mod) == list:
                name,version=mod[0],mod[1]
            elif type(mod) == str:
                (name,version)=mod.split('/')
            elif type(mod) == dict:
                name=mod['name']
                ## deal with toolkit dependency calls
                if mod.has_key('tk'):
                    version=mod['tk']
                else:
                    version=mod['version']
            else:
                log.error("Can't add module %s: unknown type"%mod)
                
            mods = self.available(name, version)
            if (name, version) in mods:
                ## ok
                self.modules.append((name, version))
            else:
                if len(mods) == 0:
                    log.warning('No module %s available'%mod)
                else:
                    log.warning('More then one module found for %s: %s'%(mod,mods))
                continue
        
    def load(self):
        """
        Load all requested modules.
        """
        for mod in self.modules:
            self.runModule('load', "/".join(mod))
    
    def runModule(self, *args, **kwargs):
        """
        Run module command.
        """
        if type(args[0]) == list:
            args = args[0]
        else:
            args = list(args)
        
        originalModulePath = os.environ['MODULEPATH']
        if kwargs.get('modulePath', None):
            os.environ['MODULEPATH'] = kwargs.get('modulePath')
        
        proc = subprocess.Popen(['/usr/bin/modulecmd', 'python'] + args,
                                stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        # stdout will contain python code (to change environment etc)
        # stderr will contain text (just like the normal module command)
        (stdout, stderr) = proc.communicate()
        os.environ['MODULEPATH'] = originalModulePath

        # Change the environment
        exec stdout

        # Process stderr
        result = []
        for line in stderr.split('\n'): #IGNORE:E1103
            if outputMatchers['whitespace'].search(line):
                continue
            
            error = outputMatchers['error'].search(line)
            if error:
                log.error(line)
                raise EasyBuildError(line)

            packages = outputMatchers['available'].finditer(line)
            for package in packages:
                result.append(package.groupdict())
        return result


def searchModule(path, query):
    """
    Search for a particular module (only prints)
    """
    print "Searching for %s in %s " % (query.lower(), path)

    query = query.lower()
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            filename = os.path.join(dirpath, filename)
            if filename.lower().find(query) != -1:
                print "- %s" % filename

        # TODO: get directories to ignore from  easybuild.tools.repository ?
        try:
            dirnames.remove('.svn')
        except ValueError: 
            pass

        try:
            dirnames.remove('.git')
        except ValueError: 
            pass

def getSoftwareRoot(name):
    """
    Return the software root set for a particular package.
    """
    environmentKey = "SOFTROOT%s" % convertName(name, upper=True)
    return os.getenv(environmentKey)

if __name__ == '__main__':
    # Run some tests, run as python -m easybuild.tools.modules
    initLogger(debug=True,typ=None)   

    testmods=Modules()
    ms=testmods.available('',None)
    ## pick one
    if len(ms) == 0:
        print "No modules found"
    else:
        import random
        m=random.choice(ms)
        print "selected module %s"%m
        testmods.addModule([m])
        testmods.load()

