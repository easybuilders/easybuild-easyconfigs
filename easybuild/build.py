#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman, Toon Willems
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
import os
import re
import shutil
import sys
import tempfile
import time
import copy
import platform
from easybuild.framework.application import Application, get_instance
from easybuild.tools.build_log import EasyBuildError, initLogger, \
    removeLogHandler, print_msg
from easybuild.tools.class_dumper import dumpClasses
from easybuild.tools.modules import Modules, searchModule
from easybuild.tools.repository import getRepository
from optparse import OptionParser
import easybuild
import easybuild.tools.config as config
import easybuild.tools.filetools as filetools
from easybuild.tools import systemtools

"""
Main entry point for EasyBuildBuild: build software from .eb input file
"""


# applications use their own logger, we need to tell them to debug or not
# so this global var is used.
LOGDEBUG = False

def add_build_options(parser):
    """
    Add build options to options parser
    """
    parser.add_option("-C", "--config",
                        help = "path to EasyBuild config file [default: $EASYBUILDCONFIG or easybuild/easybuild_config.py]")
    parser.add_option("-r", "--robot", metavar="path",
                        help="path to search for easyconfigs for missing dependencies")

    parser.add_option("-a", "--avail-easyconfig-params", action="store_true", help="show available easyconfig parameters")
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
    parser.add_option("-s", "--stop", type="choice", choices=stop_options,
                        help="stop the installation after certain step" \
                               "(valid: %s)" % ', '.join(stop_options))
    parser.add_option("-b", "--only-blocks", metavar="blocks", help="Only build blocks blk[,blk2]")
    parser.add_option("-k", "--skip", action="store_true",
                        help="skip existing software (useful for installing additional packages)")
    parser.add_option("-t", "--skip-tests", action="store_true",
                        help="skip testing")
    parser.add_option("-f", "--force", action="store_true", dest="force",
                        help="force to rebuild software even if it's already installed (i.e. can be found as module)")

    parser.add_option("-l", action="store_true", dest="stdoutLog", help="log to stdout")
    parser.add_option("-d", "--debug" , action="store_true", help="log debug messages")
    parser.add_option("-v", "--version", action="store_true", help="show version")
    parser.add_option("--regtest", action="store_true", help="enable regression test mode")
    parser.add_option("--regtest-online", action="store_true", help="enable online regression test mode")

def main():
    """
    Main function:
    - parse command line options
    - initialize logger
    - read easyconfig
    - build software
    """
    # disallow running EasyBuild as root
    if os.getuid() == 0:
        sys.stderr.write("ERROR: You seem to be running EasyBuild with root priveleges.\n" \
                        "That's not wise, so let's end this here.\n" \
                        "Exiting.\n")
        sys.exit(1)

    # options parser
    parser = OptionParser()

    parser.usage = "%prog [options] easyconfig [..]"
    parser.description = "Builds software package based on easyconfig (or parse a directory)\n" \
                         "Provide one or more easyconfigs or directories, use -h or --help more information."

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
        print_msg("This is EasyBuild %s" % easybuild.VERBOSE_VERSION, log)

    ## Initialize configuration
    # - check environment variable EASYBUILDCONFIG
    # - then, check command line option
    # - last, use default config file easybuild_config.py in build.py directory
    config_file = options.config
    if not config_file and os.getenv('EASYBUILDCONFIG'):
        config_file = os.getenv('EASYBUILDCONFIG')
    else:
        appPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        config_file = os.path.join(appPath, "easybuild_config.py")
    config.init(config_file, **configOptions)

    ## Dump possible options
    if options.avail_easyconfig_params:
        app = get_instance(options.easyblock, log)
        app.dump_cfg_options()

    ## Dump available classes
    if options.dump_classes:
        dumpClasses('easybuild.easyblocks')

    ## Search for modules
    if options.search:
        if not options.robot:
            error("Please provide a search-path to --robot when using --search")
        searchModule(options.robot, options.search)

    if options.avail_easyconfig_params or options.dump_classes or options.search or options.version:
        if logFile:
            os.remove(logFile)
        sys.exit(0)

    ## Read easyconfig files
    packages = []
    if len(paths) == 0:
        error("Please provide one or more easyconfig files", optparser=parser)

    for path in paths:
        path = os.path.abspath(path)
        if not (os.path.exists(path)):
            error("Can't find path %s" % path)

        try:
            packages.extend(findEasyconfigs(path, log, blocks, options.regtest_online))
        except IOError, err:
            log.error("Processing easyconfigs in path %s failed: %s" % (path, err))

    ## Before building starts, take snapshot of environment (watch out -t option!)
    origEnviron = copy.deepcopy(os.environ)
    os.chdir(os.environ['PWD'])

    ## Skip modules that are already installed unless forced
    if not options.force:
        m = Modules()
        packages, checkPackages = [], packages
        for package in checkPackages:
            module = package['module']
            mod = "%s (version %s)" % (module[0], module[1])
            modspath = os.path.join(config.installPath("mod"), 'all')
            if m.exists(module[0], module[1], modspath):
                msg = "%s is already installed (module found in %s), skipping " % (mod, modspath)
                print_msg(msg, log)
                log.info(msg)
            else:
                packages.append(package)

    ## Determine an order that will allow all specs in the set to build
    if len(packages) > 0:
        print_msg("resolving dependencies ...", log)
        orderedSpecs = resolveDependencies(packages, options.robot, log)
    else:
        print_msg("No packages left to be built.", log)
        orderedSpecs = []

    ## Build software, will exit when errors occurs (except when regtesting)
    correct_built_cnt = 0
    all_built_cnt = 0
    for spec in orderedSpecs:
        (success, _) = build(spec, options, log, origEnviron, exitOnFailure=(not options.regtest))
        if success:
            correct_built_cnt += 1
        all_built_cnt += 1

    print_msg("Build succeeded for %s out of %s" % (correct_built_cnt, all_built_cnt), log)

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
    print_msg("ERROR: %s\n" % message)
    if optparser:
        optparser.print_help()
    sys.exit(exitCode)

def findEasyconfigs(path, log, onlyBlocks=None, regtest_online=False):
    """
    Find .eb easyconfig files in path and process them
    """
    if os.path.isfile(path):
        return processEasyconfig(path, log, onlyBlocks, regtest_online)

    ## Walk through the start directory, retain all files that end in .eb
    files = []
    path = os.path.abspath(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith('.eb'):
                continue

            spec = os.path.join(dirpath, f)
            log.debug("Found easyconfig %s" % spec)
            files.append(spec)

    packages = []
    for filename in files:
        packages.extend(processEasyconfig(filename, log, onlyBlocks, regtest_online))
    return packages

def processEasyconfig(path, log, onlyBlocks=None, regtest_online=False):
    """
    Process easyconfig, returning some information for each block
    """
    blocks = retrieveBlocksInSpec(path, log, onlyBlocks)

    packages = []
    for spec in blocks:
        ## Process for dependencies and real installversionname
        ## - use mod? __init__ and importCfg are ignored.
        log.debug("Processing easyconfig %s" % spec)

        try:
            app = Application(debug=LOGDEBUG)
            app.process_ebfile(spec, regtest_online)
        except EasyBuildError, err:
            msg = "Failed to process easyconfig %s:\n%s" % (spec, err.msg)
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
    availableModules = Modules().available()
    if len(availableModules) == 0:
        log.warning("No installed modules. Your MODULEPATH is probably incomplete.")

    orderedSpecs = []
    # All available modules can be used for resolving dependencies except
    # those that will be installed
    beingInstalled = [p['module'] for p in unprocessed]
    processed = [m for m in availableModules if not m in beingInstalled]

    ## As long as there is progress in processing the modules, keep on trying
    loopcnt = 0
    maxloopcnt = 10000
    robotAddedDependency = True
    while robotAddedDependency:

        robotAddedDependency = False

        # make sure this stops, we really don't want to get stuck in an infinite loop
        loopcnt += 1
        if loopcnt > maxloopcnt:
            msg = "Maximum loop cnt %s reached, so quitting." % maxloopcnt
            log.error(msg)
            raise EasyBuildError(msg)

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
                    ## find easyconfig, might not find any
                    path = robotFindEasyconfig(log, robot, candidates[0])

                else:
                    path = None
                    log.debug("No more candidate dependencies to resolve for module %s" % str(module['module']))

                if path:
                    log.info("Robot: resolving dependency %s with %s" % (candidates[0], path))

                    processedSpecs = processEasyconfig(path, log)
                    mods = [spec['module'] for spec in processedSpecs]
                    if not candidates[0] in mods:
                        msg = "Expected easyconfig %s to resolve dependency for %s, but it does not" % (path, candidates[0])
                        msg += " (list of obtained modules after processing easyconfig: %s)" % mods
                        log.error(msg)
                        raise EasyBuildError(msg)

                    unprocessed.extend(processedSpecs)
                    robotAddedDependency = True
                    break

    ## There are dependencies that cannot be resolved
    if len(unprocessed) > 0:
        log.debug("List of unresolved dependencies: %s" % unprocessed)
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
            log.debug("Adding easyconfig %s to final list" % module['spec'])
            orderedSpecs.append(module)
            processed.append(module['module'])

    unprocessed[:] = [m for m in unprocessed if len(m['dependencies']) > 0]

    return orderedSpecs

def robotFindEasyconfig(log, path, module):
    """
    Find an easyconfig for module in path
    """
    name, version = module
    # candidate easyconfig paths
    easyconfigsPaths = [os.path.join(path, name, version + ".eb"),
                         os.path.join(path, name, "%s-%s.eb" % (name, version)),
                         os.path.join(path, name.lower()[0], name, "%s-%s.eb" % (name, version)),
                         os.path.join(path, "%s-%s.eb" % (name, version)),
                         ]
    for easyconfigPath in easyconfigsPaths:
        log.debug("Checking easyconfig path %s" % easyconfigPath)
        if os.path.isfile(easyconfigPath):
            log.debug("Found easyconfig file for %s at %s" % (module, easyconfigPath))
            return os.path.abspath(easyconfigPath)

    return None

def retrieveBlocksInSpec(spec, log, onlyBlocks):
    """
    Easyconfigs can contain blocks (headed by a [Title]-line)
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

        ## Make a new easyconfig for each block
        ## They will be processed in the same order as they are all described in the original file
        specs = []
        for block in blocks:
            name = block['name']
            if onlyBlocks and not (name in onlyBlocks):
                print_msg("Skipping block %s-%s" % (cfgName, name))
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
                msg = "Failed to write block %s to easyconfig %s" % (name, spec)
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

    print_msg("processing EasyBuild easyconfig %s" % spec, log)

    ## Restore original environment
    log.info("Resetting environment")
    filetools.errorsFoundInLog = 0
    if not filetools.modifyEnv(os.environ, origEnviron):
        error("Failed changing the environment back to original")

    cwd = os.getcwd()

    ## Load easyblock
    easyblock = options.easyblock
    if not easyblock:
        ## Try to look in .eb file
        reg = re.compile(r"^\s*easyblock\s*=(.*)$")
        for line in open(spec).readlines():
            match = reg.search(line)
            if match:
                easyblock = eval(match.group(1))
                break

    name = module['module'][0]
    try:
        app = get_instance(easyblock, log, name=name)
        log.info("Obtained application instance of for %s (easyblock: %s)" % (name, easyblock))
    except EasyBuildError, err:
        error("Failed to get application instance for %s (easyblock: %s): %s" % (name, easyblock, err.msg))

    ## Application settings
    if options.stop:
        log.debug("Stop set to %s" % options.stop)
        app.setcfg('stop', options.stop)

    if options.skip:
        log.debug("Skip set to %s" % options.skip)
        app.setcfg('skip', options.skip)

    app.logdebug = options.debug

    ## Build easyconfig
    errormsg = '(no error)'
    # timing info
    starttime = time.time()
    try:
        result = app.autobuild(spec, runTests=not options.skip_tests, regtest_online=options.regtest_online)
    except EasyBuildError, err:
        lastn = 300
        errormsg = "autoBuild Failed (last %d chars): %s" % (lastn, err.msg[-lastn:])
        log.exception(errormsg)
        result = False

    ended = "ended"

    ## Successful build
    if result:

        ## Collect build stats
        log.info("Collecting build stats...")
        buildtime = round(time.time() - starttime, 2)
        installsize = 0
        try:
            # change to home dir, to avoid that cwd no longer exists
            os.chdir(os.getenv('HOME'))

            # walk install dir to determine total size
            for dirpath, _, filenames in os.walk(app.installdir):
                for filename in filenames:
                    fullpath = os.path.join(dirpath, filename)
                    if os.path.exists(fullpath):
                        installsize += os.path.getsize(fullpath)
        except OSError, err:
            log.error("Failed to determine install size: %s" % err)

        currentbuildstats = bool(app.getcfg('buildstats'))
        buildstats = {'build_time' : buildtime,
                 'platform' : platform.platform(),
                 'core_count' : systemtools.get_core_count(),
                 'cpu_model': systemtools.get_cpu_model(),
                 'install_size' : installsize,
                 'timestamp' : int(time.time()),
                 'host' : os.uname()[1],
                 }
        log.debug("Build stats: %s" % buildstats)

        if app.getcfg('stop'):
            ended = "STOPPED"
            newLogDir = os.path.join(app.builddir, config.logPath())
        else:
            newLogDir = os.path.join(app.installdir, config.logPath())

            try:
                ## Upload spec to central repository
                repo = getRepository()
                if 'originalSpec' in module:
                    repo.addEasyconfig(module['originalSpec'], app.name(), app.installversion + ".block", buildstats, currentbuildstats)
                repo.addEasyconfig(spec, app.name(), app.installversion, buildstats, currentbuildstats)
                repo.commit("Built %s/%s" % (app.name(), app.installversion))
                del repo
            except EasyBuildError, err:
                log.warn("Unable to commit easyconfig to repository (%s)", err)

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
            error("Failed to move easyconfig %s to log dir %s: %s" % (spec, newLogDir, err))

    ## Build failed
    else:
        exitCode = 1
        summary = "FAILED"

        buildDir = ''
        if app.builddir:
            buildDir = " (build directory: %s)" % (app.builddir)
        succ = "unsuccessfully%s:\n%s" % (buildDir, errormsg)

        ## Cleanup logs
        app.closelog()
        applicationLog = app.logfile

    print_msg("%s: Installation %s %s" % (summary, ended, succ), log)

    ## Check for errors
    if exitCode > 0 or filetools.errorsFoundInLog > 0:
        print_msg("\nWARNING: Build exited with exit code %d. %d possible error(s) were detected in the " \
                  "build logs, please verify the build.\n" % (exitCode, filetools.errorsFoundInLog),
                  log)

    if app.postmsg:
        print_msg("\nWARNING: %s\n" % app.postmsg, log)

    print_msg("Results of the build can be found in the log file %s" % applicationLog, log)

    del app
    os.chdir(cwd)

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
    except EasyBuildError, e:
        sys.stderr.write('ERROR: %s\n' % e.msg)
        sys.exit(1)
