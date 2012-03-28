#!/usr/bin/env python
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
Main entry point for EasyBuildBuild: build software from .eb input file
"""
from optparse import OptionParser
import copy
import re
import os
import shutil
import sys
import tempfile

import easybuild
from easybuild.framework.application import Application, get_instance
from easybuild.tools.build_log import initLogger, removeLogHandler, EasyBuildError
from easybuild.tools.class_dumper import dumpClasses
import easybuild.tools.config as config
import easybuild.tools.filetools as filetools

# applications use their own logger, we need to tell them to debug or not
# so this global var is used.
LOGDEBUG = False

def add_build_options(parser):
    """
    Add build options to options parser
    """
    parser.add_option("-C", "--config",

                        help = "path to EasyBuild config file [default: easybuild_config.py in the EasyBuild directory]")
    parser.add_option("-r", "--robot", metavar="path",
                        help = "path to search for specifications for missing dependencies")

    parser.add_option("-o", "--options", action="store_true", help="show available configuration options")
    parser.add_option("--dump-classes", action="store_true", help="show classes available")
    parser.add_option("--search", help="search for module-files in the robot-directory")

    parser.add_option("-e", "--easyblock", metavar="easyblock.class",
                        help="loads the class from module to process the spec file or dump " \
                               "the options for [default: Application class]")
    parser.add_option("-p", "--pretend", action="store_true",
                        help="does the build/installation in a test directory " \
                               "located in $HOME/easybuildinstall")

    stop_options = ['cfg', 'source', 'patch', 'configure', 'make', 'install', 
                   'test', 'postproc', 'cleanup', 'packages']
    parser.add_option("-s", "--stop", type = "choice", choices = stop_options,
                        help = "stop the installation after certain step" \
                               "(valid: %s)" % ', '.join(stop_options))
    parser.add_option("-b", "--only-blocks", metavar = "blocks", help = "Only build blocks blk[,blk2]")
    parser.add_option("-k", "--skip", action = "store_true",
                        help = "skip existing software (useful for installing additional packages)")
    parser.add_option("-t", "--skip-tests", action = "store_true",
                        help = "skip testing")
    parser.add_option("-f", "--force", action = "store_true", dest="force",
                        help = "force to rebuild software even if it's already installed (i.e. can be found as module)")
    
    parser.add_option("-l", action = "store_true", dest = "stdoutLog", help = "log to stdout")
    parser.add_option("-d", "--debug" , action = "store_true", help = "log debug messages")
    parser.add_option("-v", "--version", action = "store_true", help = "show version")


def main():
    """
    Main function:
    - parse command line options
    - initialize logger
    - read specification file
    - build software
    """
    # disallow running EasyBuild as root
    if (os.getuid() == 0) or (os.getlogin() == 'root'):
        sys.stderr.write("ERROR: You seem to be running EasyBuild with root priveleges.\n" + 
                        "That's not wise, so let's end this here.\n" + 
                        "Exiting.\n")
        sys.exit(1)

    # options parser
    parser = OptionParser()

    parser.usage = "%prog [options] specification [..]"
    parser.description = "Builds software package based on specification file (or parse a directory)\n" \
                         "Provide one or more specification files or directories, use -h or --help more information."

    add_build_options(parser)

    (options, paths) = parser.parse_args()

    ## mkstemp returns (fd,filename), fd is from os.open, not regular open!
    fd, logFile = tempfile.mkstemp(suffix='.log', prefix='easybuild-')
    os.close(fd)

    if options.stdoutLog:
        os.remove(logFile)
        logFile = None

    global LOGDEBUG
    LOGDEBUG = options.debug

    configOptions = {}
    if options.pretend:
        configOptions['installPath'] = os.path.join(os.environ['HOME'], 'easybuildinstall')

    if options.only_blocks:
        blocks = options.only_blocks.split(',')
    else:
        blocks = None

    ## Initialize logger
    logFile, log, hn = initLogger(filename=logFile, debug=options.debug, typ=None)

    ## Show version
    if options.version:
        print "This is EasyBuild %s" % easybuild.VERBOSE_VERSION

    ## Initialize configuration
    # - check environment variable EASYBUILDCONFIG
    # - then, check command line option
    # - last, use default config file easybuild_config.py in build.py directory
    config_file = os.getenv('EASYBUILDCONFIG')
    if not config_file and options.config:
        config_file = options.config
    else:
        appPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        config_file = os.path.join(appPath, "easybuild_config.py")
    config.init(config_file, **configOptions)

    ## Dump possible options
    if options.options:
        app = get_instance(options.easyblock, log)
        app.dump_cfg_options()

    ## Dump available classes
    if options.dump_classes:
        dumpClasses('easybuild.easyblocks')

    ## Search for modules
    if options.search:
        if not options.robot:
            error("Please provide a search-path to --robot when using --search")
        from easybuild.tools.modules import searchModule
        searchModule(options.robot, options.search)

    if options.options or options.dump_classes or options.search or options.version:
        if logFile:
            os.remove(logFile)
        sys.exit(0)

    ## Read specification files
    packages = []
    if len(paths) == 0:
        error("Please provide one or more specification files", optparser = parser)

    for path in paths:
        path = os.path.abspath(path)
        if not (os.path.exists(path)):
            error("Can't find path %s" % path)

        try:
            packages.extend(findSpecifications(path, log, blocks))
        except IOError, err:
            log.error("Processing specifications in path %s failed: %s" % (path, err))

    ## Before building starts, take snapshot of environment (watch out -t option!)
    origEnviron = copy.deepcopy(os.environ)
    os.chdir(os.environ['PWD'])

    ## Skip modules that are already installed unless forced
    if not options.force:
        from easybuild.tools.modules import Modules
        m = Modules()
        packages, checkPackages = [], packages
        for package in checkPackages:
            module = package['module']
            mod = "%s (version %s)" % (module[0], module[1])
            modspath = os.path.join(config.installPath("mod"), 'all')
            if m.exists(module[0], module[1], modspath):
                msg = "%s is already installed (module found in %s), skipping " % (mod, modspath)
                print msg
                log.info(msg)
            else:
                packages.append(package)

    ## Determine an order that will allow all specs in the set to build
    if len(packages) > 0:
        orderedSpecs = resolveDependencies(packages, options.robot, log)
    else:
        print "No packages left to be built."
        orderedSpecs = []

    ## Build software, will exit when errors occurs
    for spec in orderedSpecs:
        build(spec, options, log, origEnviron)

    ## Cleanup tmp log file (all is well, all modules have their own log file)
    try:
        removeLogHandler(hn)
        hn.close()
        if logFile:
            os.remove(logFile)

        for package in packages:
            if 'originalSpec' in package:
                os.remove(package['spec'])

    except IOError, err:
        error("Something went wrong closing and removing the log %s : %s" % (logFile, err))

def error(message, exitCode=1, optparser=None):
    """
    Print error message and exit EasyBuild
    """
    print "ERROR: %s\n" % message
    if optparser:
        optparser.print_help()
    sys.exit(exitCode)

def findSpecifications(path, log, onlyBlocks=None):
    """
    Find .eb specification files in path and process them
    """
    if os.path.isfile(path):
        return processSpecification(path, log, onlyBlocks)

    ## Walk through the start directory
    files = []
    path = os.path.abspath(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith('.eb'):
                continue

            spec = os.path.join(dirpath, f)
            log.debug("Found specification %s" % spec)
            files.append(spec)

    packages = []
    for filename in files:
        packages.extend(processSpecification(filename, log, onlyBlocks))
    return packages

def processSpecification(path, log, onlyBlocks=None):
    """
    Process specification, returning some information for each block
    """
    blocks = retrieveBlocksInSpec(path, log, onlyBlocks)

    packages = []
    for spec in blocks:
        ## Process for dependencies and real installversionname
        ## - use mod? __init__ and importCfg are ignored.
        log.debug("Processing specification %s" % spec)

        try:
            app = Application(debug=LOGDEBUG)
            app.process_ebfile(spec)
        except EasyBuildError, err:
            msg = "Failed to process specification file %s:\n%s" % (spec, err.msg)
            log.exception(msg)
            raise EasyBuildError(msg)

        ## this app will appear as following module in the list
        package = {
            'spec': spec,
            'module': (app.name(), app.installversion),
            'dependencies': []
        }
        if len(blocks) > 1:
            package['originalSpec'] = path

        for d in app.dep:
            dep = (d['name'], d['tk'])
            log.debug("Adding dependency %s for app %s." % (dep, app.name()))
            package['dependencies'].append(dep)

        if app.tk.name != 'dummy':
            dep = (app.tk.name, app.tk.version)
            log.debug("Adding toolkit %s as dependency for app %s." % (dep, app.name()))
            package['dependencies'].append(dep)

        try:
            app.closelog()
            os.remove(app.logfile)
        except:
            msg = "Failed to remove log file %s" % app.logfile
            log.exception(msg)
            raise EasyBuildError(msg)
        del app

        packages.append(package)

    return packages

def resolveDependencies(unprocessed, robot, log):
    """
    Work through the list of packages to determine an optimal order
    """

    ## Get a list of all available modules (format: [(name, installversion), ...])
    from easybuild.tools.modules import Modules
    availableModules = Modules().available()
    if len(availableModules) == 0:
        log.warning("No installed modules. Your MODULEPATH is probably incomplete.")

    orderedSpecs = []
    # All available modules can be used for resolving dependencies except
    # those that will be installed
    beingInstalled = [p['module'] for p in unprocessed]
    processed = [m for m in availableModules if not m in beingInstalled]

    ## As long as there is progress in processing the modules, keep on trying
    robotAddedDependency = True
    while robotAddedDependency:
        robotAddedDependency = False

        ## First try resolving dependencies without using external dependencies
        lastProcessedCount = -1
        while len(processed) > lastProcessedCount:
            lastProcessedCount = len(processed)
            orderedSpecs.extend(findResolvedModules(unprocessed, processed, log))

        ## Robot: look for an existing dependency, add one
        if robot and len(unprocessed) > 0:
            beingInstalled = [p['module'] for p in unprocessed]
            for module in unprocessed:
                ## Do not choose a module that is being installed in the current run
                ## if they depend, you probably want to rebuild them using the new dependency
                candidates = [d for d in module['dependencies'] if not d in beingInstalled]
                if len(candidates) > 0:
                    path = robotFindSpecification(robot, candidates[0])
                else:
                    path = None

                if path:
                    log.info("Robot: resolving dependency %s with %s" % (candidates[0], path))
                    unprocessed.extend(processSpecification(path, log))
                    robotAddedDependency = True
                    break

    ## There are dependencies that cannot be resolved
    if len(unprocessed) > 0:
        missingDependencies = {}
        for module in unprocessed:
            for dep in module['dependencies']:
                missingDependencies[dep] = True

        msg = "Dependencies not met. Cannot resolve %s" % missingDependencies.keys()
        log.error(msg)
        raise EasyBuildError(msg)

    log.info("Dependency resolution complete, building as follows:\n%s" % orderedSpecs)
    return orderedSpecs

def findResolvedModules(unprocessed, processed, log):
    """
    Find modules in unprocessed which can be fully resolved using packages in processed
    """
    orderedSpecs = []

    for module in unprocessed:
        module['dependencies'] = [d for d in module['dependencies'] if not d in processed]

        if len(module['dependencies']) == 0:
            log.debug("Adding specification %s to final list" % module['spec'])
            orderedSpecs.append(module)
            processed.append(module['module'])

    unprocessed[:] = [m for m in unprocessed if len(m['dependencies']) > 0]

    return orderedSpecs

def robotFindSpecification(path, module):
    """
    Find a specification file for module in path
    """
    name, version = module
    specificationPath = os.path.join(path, name, version + ".eb")
    if os.path.isfile(specificationPath):
        return os.path.abspath(specificationPath)
    else:
        return None

def retrieveBlocksInSpec(spec, log, onlyBlocks):
    """
    EasyBuild-specification files can contain blocks (headed by a [Title]-line)
    which contain commands specific to that block. Commands in the beginning of the file
    above any block headers are common and shared between each block.
    """
    regBlock = re.compile(r"^\s*\[([\w.-]+)\]\s*$", re.M)
    regDepBlock = re.compile(r"^\s*block\s*=(\s*.*?)\s*$", re.M)

    cfgName = os.path.basename(spec)
    pieces = regBlock.split(open(spec).read())

    ## The first block contains common statements
    common = pieces.pop(0)
    if pieces:
        ## Make a map of blocks
        blocks = []
        while pieces:
            blockName = pieces.pop(0)
            blockContents = pieces.pop(0)

            if blockName in [b['name'] for b in blocks]:
                msg = "Found block %s twice in %s." % (blockName, spec)
                log.error(msg)
                raise EasyBuildError(msg)

            block = {'name': blockName, 'contents': blockContents}

            ## Dependency block
            depBlock = regDepBlock.search(blockContents)
            if depBlock:
                dependencies = eval(depBlock.group(1))
                if type(dependencies) == list:
                    block['dependencies'] = dependencies
                else:
                    block['dependencies'] = [dependencies]

            blocks.append(block)

        ## Make a new specification for each block
        ## They will be processed in the same order as they are all described in the original file
        specs = []
        for block in blocks:
            name = block['name']
            if onlyBlocks and not (name in onlyBlocks):
                print "Skipping block %s-%s" % (cfgName, name)
                continue

            (fd, blockPath) = tempfile.mkstemp(prefix='easybuild-', suffix='%s-%s' % (cfgName, name))
            os.close(fd)
            try:
                f = open(blockPath, 'w')
                f.write(common)

                if 'dependencies' in block:
                    for dep in block['dependencies']:
                        if not dep in [b['name'] for b in blocks]:
                            msg = "Block %s depends on %s, but block was not found." % (name, dep)
                            log.error(msg)
                            raise EasyBuildError(msg)

                        dep = [b for b in blocks if b['name'] == dep][0]
                        f.write("\n## Dependency block %s" % (dep['name']))
                        f.write(dep['contents'])

                f.write("\n## Main block %s" % name)
                f.write(block['contents'])
                f.close()

            except Exception:
                msg = "Failed to write block %s to specification file %s" % (name, spec)
                log.exception(msg)
                raise EasyBuildError(msg)

            specs.append(blockPath)

        log.debug("Found %s block(s) in %s" % (len(specs), spec))
        return specs
    else:
        ## no blocks, one file
        return [spec]

def build(module, options, log, origEnviron, exitOnFailure=True):
    """
    Build the software
    """
    spec = module['spec']

    print "processing EasyBuild specification file %s" % spec

    ## Restore original environment
    log.info("Resetting environment")
    filetools.errorsFoundInLog = 0
    if not filetools.modifyEnv(os.environ, origEnviron):
        error("Failed changing the environment back to original")

    cwd = os.getcwd()

    ## Load applicationclass
    easyblock = options.easyblock
    if not easyblock:
        ## Try to look in spec file
        reg = re.compile(r"^\s*easyblock\s*=(.*)$")
        for line in open(spec).readlines():
            match = reg.search(line)
            if match:
                easyblock = eval(match.group(1))
                break

    try:
        app = get_instance(easyblock, log, name=module['module'][0])
    except (ImportError, NameError), err:
        error("Failed to get application instance of class %s: %s" % (applicationClass, err))

    ## Application settings
    if options.stop:
        log.debug("Stop set to %s" % options.stop)
        app.setcfg('stop', options.stop)

    if options.skip:
        log.debug("Skip set to %s" % options.skip)
        app.setcfg('skip', options.skip)

    app.logdebug = options.debug

    ## Build specification
    try:
        result = app.autobuild(spec, runTests=not options.skip_tests)
    except EasyBuildError, err:
        msg = "autoBuild Failed: %s" % err
        log.exception(msg)
        result = False

    ended = "ended"

    ## Successful build
    if result:
        if app.getcfg('stop'):
            ended = "STOPPED"
            newLogDir = os.path.join(app.builddir, config.logPath())
        else:
            newLogDir = os.path.join(app.installdir, config.logPath())

            try:
                ## Upload spec to central repository
                from easybuild.tools.repository import getRepository
                repo = getRepository()
                if 'originalSpec' in module:
                    repo.addSpecFile(module['originalSpec'], app.name(), app.installversion + ".block")
                repo.addSpecFile(spec, app.name(), app.installversion)
                repo.commit("Built %s/%s" % (app.name(), app.installversion))
                del repo
            except EasyBuildError, err:
                log.warn("Unable to commit specification-file to repository (%s)", err)

        exitCode = 0
        succ = "successfully"
        summary = "COMPLETED"

        ## Cleanup logs
        app.closelog()
        try:
            if not os.path.isdir(newLogDir):
                os.makedirs(newLogDir)
            applicationLog = os.path.join(newLogDir, os.path.basename(app.logfile))
            shutil.move(app.logfile, applicationLog)
        except IOError, err:
            error("Failed to move log file %s to new log file %s: %s" % (app.logfile, applicationLog, err))

        try:
            shutil.copy(spec, os.path.join(newLogDir, "%s-%s.eb" % (app.name(), app.installversion)))
        except IOError, err:
            error("Failed to move specification file %s to log dir %s: %s" % (spec, newLogDir, err))

    ## Build failed
    else:
        exitCode = 1
        summary = "FAILED"

        buildDir = ''
        if app.builddir:
            buildDir = " (build directory: %s)" % (app.builddir)
        succ = "unsuccessfully%s" % buildDir

        ## Cleanup logs
        app.closelog()
        applicationLog = app.logfile

    del app
    os.chdir(cwd)

    print "%s: Installation %s %s." % (summary, ended, succ)

    ## Check for errors
    if exitCode > 0 or filetools.errorsFoundInLog > 0:
        print "WARNING: Build exited with exit code %d. %d possible error(s) were detected in the " \
              "build logs, please verify the build." % (exitCode, filetools.errorsFoundInLog)

    print "Results of the build can be found in the log file %s" % applicationLog

    if exitCode > 0:
        # don't exit on failure in test suite
        if exitOnFailure:
            sys.exit(exitCode)
        else:
            return (False, applicationLog)
    else:
        return (True, applicationLog)

if __name__ == "__main__":
    try:
        main()
    except EasyBuildError,e:
        sys.stderr.write('ERROR: %s\n' % e.msg)
        sys.exit(1)
