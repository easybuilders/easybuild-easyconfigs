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
Modules functionality: loading modules, checking for available modules, ...
"""
import os
import re
import subprocess
import sys

from easybuild.tools.build_log import getLog, EasyBuildError
from easybuild.tools.filetools import convertName, run_cmd


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
    def __init__(self, modulePath=None):
        self.modulePath = modulePath
        self.modules = []

        self.checkModulePath()

        # make sure environment-modules is installed
        ec = subprocess.call(["which", "modulecmd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if ec:
            msg = "Could not find the modulecmd command, environment-modules is not installed?\n"
            msg += "Exit code of 'which modulecmd': %d" % ec
            log.error(msg)
            raise EasyBuildError(msg)

    def checkModulePath(self):
        """
        Check if MODULEPATH is set and change it if necessary.
        """
        if not 'MODULEPATH' in os.environ:
            errormsg = 'MODULEPATH not found in environment'
            # check if environment-modules is found
            module_regexp = re.compile("^module is a function\s*\nmodule\s*()")
            cmd = "type module"
            (out, ec) = run_cmd(cmd, log_all=False, log_ok=False)
            if ec != 0 or not module_regexp.match(out):
                errormsg += "; environment-modules doesn't seem to be installed: "
                errormsg += "'%s' failed with exit code %s and output: '%s'" % (cmd, ec, out.strip('\n'))
            log.error(errormsg)

        if self.modulePath:
            ## set the module path environment accordingly
            os.environ['MODULEPATH'] = ":".join(self.modulePath)
        else:
            ## take module path from environment
            self.modulePath = os.environ['MODULEPATH'].split(':')

        if not 'LOADEDMODULES' in os.environ:
            os.environ['LOADEDMODULES'] = ''

    def available(self, name=None, version=None, modulePath=None):
        """
        Return list of available modules.
        """
        if not name: name = ''
        if not version: version = ''

        txt = name
        if version:
            txt = "%s/%s" % (name, version)

        modules = self.runModule('available', txt, modulePath=modulePath)

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
            if type(mod) == list or type(mod) == tuple:
                name, version = mod[0], mod[1]
            elif type(mod) == str:
                (name, version) = mod.split('/')
            elif type(mod) == dict:
                name = mod['name']
                ## deal with toolkit dependency calls
                if 'tk' in mod:
                    version = mod['tk']
                else:
                    version = mod['version']
            else:
                log.error("Can't add module %s: unknown type" % str(mod))

            mods = self.available(name, version)
            if (name, version) in mods:
                ## ok
                self.modules.append((name, version))
            else:
                if len(mods) == 0:
                    log.warning('No module %s available' % mod)
                else:
                    log.warning('More then one module found for %s: %s' % (mod, mods))
                continue

    def load(self):
        """
        Load all requested modules.
        """
        for mod in self.modules:
            self.runModule('load', "/".join(mod))

    def show(self, name, version):
        """
        Run 'module show' for the specified module.
        """
        return self.runModule('show', "%s/%s" % (name, version), return_output=True)

    def modulefile_path(self, name, version):
        """
        Get the path of the module file for the specified module
        """
        if not self.exists(name, version):
            return None
        else:
            modinfo = self.show(name, version)

            # second line of module show output contains full path of module file
            return modinfo.split('\n')[1].replace(':', '')

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

        proc = subprocess.Popen(['modulecmd', 'python'] + args,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # stdout will contain python code (to change environment etc)
        # stderr will contain text (just like the normal module command)
        (stdout, stderr) = proc.communicate()
        os.environ['MODULEPATH'] = originalModulePath

        if kwargs.get('return_output', False):
            return (stdout + stderr)

        else:
            # Change the environment
            try:
                exec stdout
            except Exception, err:
                raise EasyBuildError("Changing environment as dictated by module failed: %s" % err)

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

    def loaded_modules(self):

        loaded_modules = []
        mods = []

        if os.getenv('LOADEDMODULES'):
            mods = os.getenv('LOADEDMODULES').split(':')

        elif os.getenv('_LMFILES_'):
            mods = ['/'.join(modfile.split('/')[-2:]) for modfile in os.getenv('_LMFILES_').split(':')]

        else:
            log.debug("No environment variable found to determine loaded modules, assuming no modules are loaded.")

        # filter devel modules, since they cannot be split like this
        mods = [mod for mod in mods if not mod.endswith("easybuild-devel")]
        for mod in mods:
            (mod_name, mod_version) = mod.split('/')
            loaded_modules.append({
                                   'name':mod_name,
                                   'version':mod_version
                                   })

        return loaded_modules

    # depth=sys.maxint should be equivalent to infinite recursion depth
    def dependencies_for(self, name, version, depth=sys.maxint):
        """
        Obtain a list of dependencies for the given module, determined recursively, up to a specified depth (optionally)
        """
        modfilepath = self.modulefile_path(name, version)
        log.debug("modulefile path %s/%s: %s" % (name, version, modfilepath))

        try:
            f = open(modfilepath, "r")
            modtxt = f.read()
            f.close()
        except IOError, err:
            log.error("Failed to read module file %s to determine toolkit dependencies: %s" % (modfilepath, err))

        loadregex = re.compile("^\s+module load\s+(.*)$", re.M)
        mods = [mod.split('/') for mod in loadregex.findall(modtxt)]

        if depth > 0:
            # recursively determine dependencies for these dependency modules, until depth is non-positive
            moddeps = [self.dependencies_for(modname, modversion, depth=depth-1) for (modname, modversion) in mods]
        else:
            # ignore any deeper dependencies
            moddeps = []

        deps = [{'name':modname, 'version':modversion} for (modname, modversion) in mods]

        # add dependencies of dependency modules only if they're not there yet
        for moddepdeps in moddeps:
            for dep in moddepdeps:
                if not dep in deps:
                    deps.append(dep)

        return deps


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
        # remove all hidden directories?:
        #dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        try:
            dirnames.remove('.svn')
        except ValueError:
            pass

        try:
            dirnames.remove('.git')
        except ValueError:
            pass

def get_software_root(name, with_env_var=False):
    """
    Return the software root set for a particular package.
    """
    name = convertName(name, upper=True)
    environment_key = "EBROOT%s" % name
    legacy_key = "SOFTROOT%s" % name

    # keep on supporting legacy installations
    if environment_key in os.environ:
        env_var = environment_key
    else:
        env_var = legacy_key

    root = os.getenv(env_var)

    if with_env_var:
        return (root, env_var)
    else:
        return root

def get_software_version(name):
    """
    Return the software version set for a particular package.
    """
    name = convertName(name, upper=True)
    environment_key = "EBVERSION%s" % name
    legacy_key = "SOFTVERSION%s" % name

    # keep on supporting legacy installations
    if environment_key in os.environ:
        return os.getenv(environment_key)
    else:
        return os.getenv(legacy_key)

def curr_module_paths():
    """
    Return a list of current module paths.
    """
    return os.environ['MODULEPATH'].split(':')

def mk_module_path(paths):
    """
    Create a string representing the list of module paths.
    """
    return ':'.join(paths)
