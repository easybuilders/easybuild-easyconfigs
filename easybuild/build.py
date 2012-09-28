#!/usr/bin/env python
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
Main entry point for EasyBuild: build software from .eb input file
"""

import copy
import platform
import os
import re
import shutil
import sys
import tempfile
import time
from optparse import OptionParser, OptionGroup

# optional Python packages, these might be missing
# failing imports are just ignored
# a NameError should be catched where these are used

# PyGraph (used for generating dependency graphs)
try:
    import  pygraph.readwrite.dot as dot
    from pygraph.classes.digraph import digraph
except ImportError, err:
    pass

# graphviz (used for creating dependency graph images)
try:
    sys.path.append('..')
    sys.path.append('/usr/lib/graphviz/python/')
    sys.path.append('/usr/lib64/graphviz/python/')
    import gv
except ImportError, err:
    pass

import easybuild  # required for VERBOSE_VERSION
import easybuild.framework.easyconfig as easyconfig
import easybuild.tools.config as config
import easybuild.tools.filetools as filetools
import easybuild.tools.parallelbuild as parbuild
from easybuild.framework.application import get_class
from easybuild.framework.easyconfig import EasyConfig
from easybuild.tools.build_log import EasyBuildError, initLogger, \
    removeLogHandler, print_msg
from easybuild.tools.class_dumper import dumpClasses
from easybuild.tools.modules import Modules, searchModule, \
    curr_module_paths, mk_module_path
from easybuild.tools.config import getRepository
from easybuild.tools import systemtools


# applications use their own logger, we need to tell them to debug or not
# so this global variable is used.
LOGDEBUG = False

def add_cmdline_options(parser):
    """
    Add build options to options parser
    """
    # runtime options
    basic_options = OptionGroup(parser, "Basic options", "Basic runtime options for EasyBuild.")

    basic_options.add_option("-b", "--only-blocks", metavar="BLOCKS", help="Only build blocks blk[,blk2]")
    basic_options.add_option("-d", "--debug" , action="store_true", help="log debug messages")
    basic_options.add_option("-f", "--force", action="store_true", dest="force",
                        help="force to rebuild software even if it's already installed (i.e. can be found as module)")
    basic_options.add_option("--job", action="store_true", help="will submit the build as a job")
    basic_options.add_option("-k", "--skip", action="store_true",
                        help="skip existing software (useful for installing additional packages)")
    basic_options.add_option("-l", action="store_true", dest="stdoutLog", help="log to stdout")
    basic_options.add_option("-r", "--robot", metavar="PATH",
                        help="path to search for easyconfigs for missing dependencies")
    basic_options.add_option("--regtest", action="store_true", help="enable regression test mode")
    basic_options.add_option("--regtest-online", action="store_true", help="enable online regression test mode")
    basic_options.add_option("-s", "--stop", type="choice", choices=EasyConfig.validstops,
                        help="stop the installation after certain step (valid: %s)" % ', '.join(EasyConfig.validstops))
    strictness_options = ['ignore', 'warn', 'error']
    basic_options.add_option("--strict", type="choice", choices=strictness_options, help="set strictness " + \
                               "level (possible levels: %s)" % ', '.join(strictness_options))

    parser.add_option_group(basic_options)

    # software build options
    software_build_options = OptionGroup(parser, "Software build options",
                                     "Specify software build options; the regular versions of these " \
                                     "options will only search for matching easyconfigs, while the " \
                                     "--try-X versions will cause EasyBuild to try and generate a " \
                                     "matching easyconfig based on available ones if no matching " \
                                     "easyconfig is found (NOTE: best effort, might produce wrong builds!)")

    list_of_software_build_options = [
                                      ('software-name', 'NAME', 'store',
                                       "build software with name"),
                                      ('software-version', 'VERSION', 'store',
                                       "build software with version"),
                                      ('toolkit', 'NAME,VERSION', 'store',
                                       "build with toolkit (name and version)"),
                                      ('toolkit-name', 'NAME', 'store',
                                       "build with toolkit name"),
                                      ('toolkit-version', 'VERSION', 'store',
                                       "build with toolkit version"),
                                      ('amend', 'VAR=VALUE[,VALUE]', 'append',
                                       "specify additional build parameters (can be used multiple times); " \
                                       "for example: versionprefix=foo or patches=one.patch,two.patch)")
                                      ]

    for (opt_name, opt_metavar, opt_action, opt_help) in list_of_software_build_options:
        software_build_options.add_option("--%s" % opt_name,
                                          metavar=opt_metavar,
                                          action=opt_action,
                                          help=opt_help)

    for (opt_name, opt_metavar, opt_action, opt_help) in list_of_software_build_options:
        software_build_options.add_option("--try-%s" % opt_name,
                                          metavar=opt_metavar,
                                          action=opt_action,
                                          help="try to %s (USE WITH CARE!)" % opt_help)

    parser.add_option_group(software_build_options)

    # override options
    override_options = OptionGroup(parser, "Override options", "Override default EasyBuild behavior.")
    
    override_options.add_option("-C", "--config",
                        help = "path to EasyBuild config file [default: $EASYBUILDCONFIG or easybuild/easybuild_config.py]")
    override_options.add_option("-e", "--easyblock", metavar="CLASS",
                        help="loads the class from module to process the spec file or dump " \
                               "the options for [default: Application class]")
    override_options.add_option("-p", "--pretend", action="store_true", help="does the build/installation in " \
                                "a test directory located in $HOME/easybuildinstall [default: $EASYBUILDINSTALLDIR " \
                                "or installPath in EasyBuild config file]")
    override_options.add_option("-t", "--skip-tests", action="store_true", help="skip testing")

    parser.add_option_group(override_options)

    # informative options
    informative_options = OptionGroup(parser, "Informative options",
                                      "Obtain information about EasyBuild.")

    informative_options.add_option("-a", "--avail-easyconfig-params", action="store_true",
                                   help="show available easyconfig parameters")
    informative_options.add_option("--dump-classes", action="store_true",
                                   help="show list of available classes")
    informative_options.add_option("--search", help="search for module-files in the robot-directory")
    informative_options.add_option("-v", "--version", action="store_true", help="show version")
    informative_options.add_option("--dep-graph", metavar="depgraph.<ext>", help="create dependency graph")

    parser.add_option_group(informative_options)


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
    parser.description = "Builds software package based on easyconfig (or parse a directory). " \
                         "Provide one or more easyconfigs or directories, use -h or --help more information."

    add_cmdline_options(parser)

    (options, paths) = parser.parse_args()

    # mkstemp returns (fd,filename), fd is from os.open, not regular open!
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

    # initialize logger
    logFile, log, hn = initLogger(filename=logFile, debug=options.debug, typ="build")

    # show version
    if options.version:
        print_msg("This is EasyBuild %s" % easybuild.VERBOSE_VERSION, log)

    # initialize configuration
    # - check environment variable EASYBUILDCONFIG
    # - then, check command line option
    # - last, use default config file easybuild_config.py in build.py directory
    config_file = options.config

    if not config_file:
        log.debug("No config file specified on command line, trying other options.")

        config_env_var = config.environmentVariables['configFile']
        if os.getenv(config_env_var):
            log.debug("Environment variable %s, so using that as config file." % config_env_var)
            config_file = os.getenv(config_env_var)
        else:
            appPath = os.path.dirname(os.path.realpath(sys.argv[0]))
            config_file = os.path.join(appPath, "easybuild_config.py")
            log.debug("Falling back to default config: %s" % config_file)

    config.init(config_file, **configOptions)

    # dump possible options
    if options.avail_easyconfig_params:
        print_avail_params(options.easyblock, log)

    # dump available classes
    if options.dump_classes:
        dumpClasses('easybuild.easyblocks')

    # search for modules
    if options.search:
        if not options.robot:
            error("Please provide a search-path to --robot when using --search")
        searchModule(options.robot, options.search)

    if options.avail_easyconfig_params or options.dump_classes or options.search or options.version:
        if logFile:
            os.remove(logFile)
        sys.exit(0)

    # set strictness of filetools module
    if options.strict:
        filetools.strictness = options.strict

    # building a dependency graph implies force, so that all dependencies are retained
    # and also skips validation of easyconfigs (e.g. checking os dependencies)
    validate_easyconfigs = True
    retain_all_deps = False
    if options.dep_graph:
        log.info("Enabling force to generate dependency graph.")
        options.force = True
        validate_easyconfigs = False
        retain_all_deps = True
    
    # process software build specifications (if any), i.e.
    # software name/version, toolkit name/version, extra patches, ...
    (try_to_generate, software_build_specs) = process_software_build_specs(options)

    if len(paths) == 0:
        if software_build_specs.has_key('name'):
            paths = [obtain_path(software_build_specs, options.robot, log, try_to_generate)]
        else:
            error("Please provide one or multiple easyconfig files, or use software build " \
                  "options to make EasyBuild search for easyconfigs", optparser=parser)

    else:
        # indicate that specified paths do not contain generated easyconfig files
        paths = [(path, False) for path in paths]

    # read easyconfig files
    packages = []
    for (path, generated) in paths:
        path = os.path.abspath(path)
        if not (os.path.exists(path)):
            error("Can't find path %s" % path)

        try:
            files = findEasyconfigs(path, log)
            for f in files:
                if not generated and try_to_generate and software_build_specs:
                    ec_file = easyconfig.tweak(f, None, software_build_specs, log)
                else:
                    ec_file = f
                packages.extend(processEasyconfig(ec_file, log, blocks, validate=validate_easyconfigs))
        except IOError, err:
            log.error("Processing easyconfigs in path %s failed: %s" % (path, err))

    # before building starts, take snapshot of environment (watch out -t option!)
    origEnviron = copy.deepcopy(os.environ)
    os.chdir(os.environ['PWD'])

    # skip modules that are already installed unless forced
    if not options.force:
        m = Modules()
        packages, checkPackages = [], packages
        for package in checkPackages:
            module = package['module']
            mod = "%s (version %s)" % (module[0], module[1])
            modspath = mk_module_path(curr_module_paths() + [os.path.join(config.installPath("mod"), 'all')])
            if m.exists(module[0], module[1], modspath):
                msg = "%s is already installed (module found in %s), skipping " % (mod, modspath)
                print_msg(msg, log)
                log.info(msg)
            else:
                log.debug("%s is not installed yet, so retaining it" % mod)
                packages.append(package)

    # determine an order that will allow all specs in the set to build
    if len(packages) > 0:
        print_msg("resolving dependencies ...", log)
        # force all dependencies to be retained and validation to be skipped for building dep graph
        force = retain_all_deps and not validate_easyconfigs
        orderedSpecs = resolveDependencies(packages, options.robot, log, force=force)
    else:
        print_msg("No packages left to be built.", log)
        orderedSpecs = []

    # create dependency graph and exit
    if options.dep_graph:
        log.info("Creating dependency graph %s" % options.dep_graph)
        try:
            dep_graph(options.dep_graph, orderedSpecs, log)
        except NameError, err:
            log.error("At least one optional Python packages (pygraph, dot, graphviz) required to " \
                      "generate dependency graphs is missing: %s" % err)
        sys.exit(0)

    # submit build as job(s) and exit
    if options.job:
        curdir = os.getcwd()
        easybuild_basedir = os.path.dirname(os.path.dirname(sys.argv[0]))
        eb_path = os.path.join(easybuild_basedir, "eb")

        # Reverse option parser -> string

        # the options to ignore
        ignore = map(parser.get_option, ['--robot', '--help', '--job'])

        # loop over all the different options.
        result_opts = []
        relevant_opts = [o for o in parser.option_list if o not in ignore]
        for opt in relevant_opts:
            value = getattr(options, opt.dest)
            # explicit check for None (some option are store_false)
            if value != None:
                # get_opt_string is not documented (but is a public method)
                name = opt.get_opt_string()
                if opt.action == 'store':
                    result_opts.append("%s %s" % (name, value))
                else:
                    result_opts.append(name)

        opts = ' '.join(result_opts)

        command = "cd %s && %s %%s %s" % (curdir, eb_path, opts)
        jobs = parbuild.build_packages_in_parallel(command, orderedSpecs, "easybuild-build", log)
        print "List of submitted jobs:"
        for job in jobs:
            print "%s: %s" % (job.name, job.jobid)
        print "(%d jobs submitted)" % len(jobs)

        log.info("Submitted parallel build jobs, exiting now")
        sys.exit(0)

    # build software, will exit when errors occurs (except when regtesting)
    correct_built_cnt = 0
    all_built_cnt = 0
    for spec in orderedSpecs:
        (success, _) = build(spec, options, log, origEnviron, exitOnFailure=(not options.regtest))
        if success:
            correct_built_cnt += 1
        all_built_cnt += 1

    print_msg("Build succeeded for %s out of %s" % (correct_built_cnt, all_built_cnt), log)

    getRepository().cleanup()
    # cleanup tmp log file (all is well, all modules have their own log file)
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
        print_msg("ERROR: %s\n" % message)
    sys.exit(exitCode)

def warning(message):
    """
    Print warning message.
    """
    print_msg("WARNING: %s\n" % message)

def findEasyconfigs(path, log):
    """
    Find .eb easyconfig files in path
    """
    if os.path.isfile(path):
        return [path]

    # walk through the start directory, retain all files that end in .eb
    files = []
    path = os.path.abspath(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith('.eb'):
                continue

            spec = os.path.join(dirpath, f)
            log.debug("Found easyconfig %s" % spec)
            files.append(spec)

    return files

def processEasyconfig(path, log, onlyBlocks=None, regtest_online=False, validate=True):
    """
    Process easyconfig, returning some information for each block
    """
    blocks = retrieveBlocksInSpec(path, log, onlyBlocks)

    packages = []
    for spec in blocks:
        # process for dependencies and real installversionname
        # - use mod? __init__ and importCfg are ignored.
        log.debug("Processing easyconfig %s" % spec)

        # create easyconfig
        try:
            ec = EasyConfig(spec, validate=validate)
        except EasyBuildError, err:
            msg = "Failed to process easyconfig %s:\n%s" % (spec, err.msg)
            log.exception(msg)

        name = ec['name']

        # this app will appear as following module in the list
        package = {
            'spec': spec,
            'module': (ec.name(), ec.installversion()),
            'dependencies': []
        }
        if len(blocks) > 1:
            package['originalSpec'] = path

        for d in ec.dependencies():
            dep = (d['name'], d['tk'])
            log.debug("Adding dependency %s for app %s." % (dep, name))
            package['dependencies'].append(dep)

        if ec.toolkit_name() != 'dummy':
            dep = (ec.toolkit_name(), ec.toolkit_version())
            log.debug("Adding toolkit %s as dependency for app %s." % (dep, name))
            package['dependencies'].append(dep)

        del ec

        # this is used by the parallel builder
        package['unresolvedDependencies'] = copy.copy(package['dependencies'])

        packages.append(package)

    return packages

def resolveDependencies(unprocessed, robot, log, force=False):
    """
    Work through the list of packages to determine an optimal order
    enabling force results in retaining all dependencies and skipping validation of easyconfigs
    """

    if force:
        # assume that no modules are available when forced
        availableModules = []
        log.info("Forcing all dependencies to be retained.")
    else:
        # Get a list of all available modules (format: [(name, installversion), ...])
        availableModules = Modules().available()

        if len(availableModules) == 0:
            log.warning("No installed modules. Your MODULEPATH is probably incomplete.")

    orderedSpecs = []
    # All available modules can be used for resolving dependencies except
    # those that will be installed
    beingInstalled = [p['module'] for p in unprocessed]
    processed = [m for m in availableModules if not m in beingInstalled]

    # as long as there is progress in processing the modules, keep on trying
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

        # first try resolving dependencies without using external dependencies
        lastProcessedCount = -1
        while len(processed) > lastProcessedCount:
            lastProcessedCount = len(processed)
            orderedSpecs.extend(findResolvedModules(unprocessed, processed, log))

        # robot: look for an existing dependency, add one
        if robot and len(unprocessed) > 0:

            beingInstalled = [p['module'] for p in unprocessed]

            for module in unprocessed:
                # do not choose a module that is being installed in the current run
                # if they depend, you probably want to rebuild them using the new dependency
                candidates = [d for d in module['dependencies'] if not d in beingInstalled]
                if len(candidates) > 0:
                    # find easyconfig, might not find any
                    path = robotFindEasyconfig(log, robot, candidates[0])

                else:
                    path = None
                    log.debug("No more candidate dependencies to resolve for module %s" % str(module['module']))

                if path:
                    log.info("Robot: resolving dependency %s with %s" % (candidates[0], path))

                    processedSpecs = processEasyconfig(path, log, validate=(not force))

                    # ensure the pathname is equal to the module
                    mods = [spec['module'] for spec in processedSpecs]
                    if not candidates[0] in mods:
                        log.error("easyconfig file %s does not contain module %s" % (path, candidates[0]))

                    unprocessed.extend(processedSpecs)
                    robotAddedDependency = True
                    break

    # there are dependencies that cannot be resolved
    if len(unprocessed) > 0:
        log.debug("List of unresolved dependencies: %s" % unprocessed)
        missingDependencies = {}
        for module in unprocessed:
            for dep in module['dependencies']:
                missingDependencies[dep] = True

        msg = "Dependencies not met. Cannot resolve %s" % missingDependencies.keys()
        log.error(msg)

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

def process_software_build_specs(options):
    """
    Create a dictionary with specified software build options.
    The options arguments should be a parsed option list (as delivered by OptionParser.parse_args)
    """

    try_to_generate = False
    buildopts = {}

    # regular options: don't try to generate easyconfig, and search
    opts_map = {
                'name': options.software_name,
                'version': options.software_version,
                'toolkit_name': options.toolkit_name,
                'toolkit_version': options.toolkit_version,
               }

    # try options: enable optional generation of easyconfig
    try_opts_map = {
                    'name': options.try_software_name,
                    'version': options.try_software_version,
                    'toolkit_name': options.try_toolkit_name,
                    'toolkit_version': options.try_toolkit_version,
                   }

    # process easy options
    for (key, opt) in opts_map.items():
        if opt:
            buildopts.update({key: opt})
            # remove this key from the dict of try-options (overruled)
            try_opts_map.pop(key)

    for (key, opt) in try_opts_map.items():
        if opt:
            buildopts.update({key: opt})
            # only when a try option is set do we enable generating easyconfigs
            try_to_generate = True

    # process --toolkit --try-toolkit
    if options.toolkit or options.try_toolkit:

        if options.toolkit:
                tk = options.toolkit.split(',')
                if options.try_toolkit:
                    warning("Ignoring --try-toolkit, only using --toolkit specification.")
        elif options.try_toollkit:
                tk = options.try_toolkit.split(',')
                try_to_generate = True
        else:
            # shouldn't happen
            error("Huh, neither --toolkit or --try-toolkit used?")

        if not len(tk) == 2:
            error("Please specify to toolkit to use as 'name,version' (e.g., 'goalf,1.1.0').")

        [toolkit_name, toolkit_version] = tk
        buildopts.update({'toolkit_name': toolkit_name})
        buildopts.update({'toolkit_version': toolkit_version})

    # process --amend and --try-amend
    if options.amend or options.try_amend:

        amends = []
        if options.amend:
            amends += options.amend
            if options.try_amend:
                warning("Ignoring options passed via --try-amend, only using those passed via --amend.")
        if options.try_amend:
            amends += options.try_amend
            try_to_generate = True

        for amend_spec in amends:
            # e.g., 'foo=bar=baz' => foo = 'bar=baz'
            param = amend_spec.split('=')[0]
            value = '='.join(amend_spec.split('=')[1:])
            # support list values by splitting on ',' if its there
            # e.g., 'foo=bar,baz' => foo = ['bar', 'baz']
            if ',' in value:
                value = value.split(',')
            buildopts.update({param: value})

    return (try_to_generate, buildopts)

def obtain_path(specs, robot, log, try_to_generate=False):
    """Obtain a path for an easyconfig that matches the given specifications."""

    # if no easyconfig files/paths were provided, but we did get a software name,
    # we can try and find a suitable easyconfig ourselves, or generate one if we can
    (generated, fn) = easyconfig.obtain_ec_for(specs, robot, None, log)
    if not generated:
        return (fn, generated)
    else:
        # if an easyconfig was generated, make sure we're allowed to use it
        if try_to_generate:
            print_msg("Generated an easyconfig file %s, going to use it now..." % fn)
            return (fn, generated)
        else:
            try:
                os.remove(fn)
            except OSError, err:
                warning("Failed to remove generated easyconfig file %s." % fn)
            error("Unable to find an easyconfig for the given specifications: %s; " \
                  "to make EasyBuild try to generate a matching easyconfig, " \
                  "use the --try-X options " % specs)


def robotFindEasyconfig(log, path, module):
    """
    Find an easyconfig for module in path
    """
    name, version = module
    # candidate easyconfig paths
    easyconfigsPaths = easyconfig.create_paths(path, name, version)
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

    # the first block contains common statements
    common = pieces.pop(0)
    if pieces:
        # make a map of blocks
        blocks = []
        while pieces:
            blockName = pieces.pop(0)
            blockContents = pieces.pop(0)

            if blockName in [b['name'] for b in blocks]:
                msg = "Found block %s twice in %s." % (blockName, spec)
                log.error(msg)

            block = {'name': blockName, 'contents': blockContents}

            # dependency block
            depBlock = regDepBlock.search(blockContents)
            if depBlock:
                dependencies = eval(depBlock.group(1))
                if type(dependencies) == list:
                    block['dependencies'] = dependencies
                else:
                    block['dependencies'] = [dependencies]

            blocks.append(block)

        # make a new easyconfig for each block
        # they will be processed in the same order as they are all described in the original file
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

                        dep = [b for b in blocks if b['name'] == dep][0]
                        f.write("\n# Dependency block %s" % (dep['name']))
                        f.write(dep['contents'])

                f.write("\n# Main block %s" % name)
                f.write(block['contents'])
                f.close()

            except Exception:
                msg = "Failed to write block %s to easyconfig %s" % (name, spec)
                log.exception(msg)

            specs.append(blockPath)

        log.debug("Found %s block(s) in %s" % (len(specs), spec))
        return specs
    else:
        # no blocks, one file
        return [spec]

def build(module, options, log, origEnviron, exitOnFailure=True):
    """
    Build the software
    """
    spec = module['spec']

    print_msg("processing EasyBuild easyconfig %s" % spec, log)

    # restore original environment
    log.info("Resetting environment")
    filetools.errorsFoundInLog = 0
    if not filetools.modifyEnv(os.environ, origEnviron):
        error("Failed changing the environment back to original")

    cwd = os.getcwd()

    # load easyblock
    easyblock = options.easyblock
    if not easyblock:
        # try to look in .eb file
        reg = re.compile(r"^\s*easyblock\s*=(.*)$")
        for line in open(spec).readlines():
            match = reg.search(line)
            if match:
                easyblock = eval(match.group(1))
                break

    name = module['module'][0]
    try:
        app_class = get_class(easyblock, log, name=name)
        app = app_class(spec, debug=options.debug)
        log.info("Obtained application instance of for %s (easyblock: %s)" % (name, easyblock))
    except EasyBuildError, err:
        error("Failed to get application instance for %s (easyblock: %s): %s" % (name, easyblock, err.msg))

    # application settings
    if options.stop:
        log.debug("Stop set to %s" % options.stop)
        app.setcfg('stop', options.stop)

    if options.skip:
        log.debug("Skip set to %s" % options.skip)
        app.setcfg('skip', options.skip)

    # build easyconfig
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

    # successful build
    if result:

        # collect build stats
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

        currentbuildstats = app.getcfg('buildstats')
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
                # upload spec to central repository
                repo = getRepository()
                if 'originalSpec' in module:
                    repo.addEasyconfig(module['originalSpec'], app.name(), app.installversion() + ".block", buildstats, currentbuildstats)
                repo.addEasyconfig(spec, app.name(), app.installversion(), buildstats, currentbuildstats)
                repo.commit("Built %s/%s" % (app.name(), app.installversion()))
                del repo
            except EasyBuildError, err:
                log.warn("Unable to commit easyconfig to repository (%s)", err)

        exitCode = 0
        succ = "successfully"
        summary = "COMPLETED"

        # cleanup logs
        app.closelog()
        try:
            if not os.path.isdir(newLogDir):
                os.makedirs(newLogDir)
            applicationLog = os.path.join(newLogDir, os.path.basename(app.logfile))
            shutil.move(app.logfile, applicationLog)
        except IOError, err:
            error("Failed to move log file %s to new log file %s: %s" % (app.logfile, applicationLog, err))

        try:
            shutil.copy(spec, os.path.join(newLogDir, "%s-%s.eb" % (app.name(), app.installversion())))
        except IOError, err:
            error("Failed to move easyconfig %s to log dir %s: %s" % (spec, newLogDir, err))

    # build failed
    else:
        exitCode = 1
        summary = "FAILED"

        buildDir = ''
        if app.builddir:
            buildDir = " (build directory: %s)" % (app.builddir)
        succ = "unsuccessfully%s:\n%s" % (buildDir, errormsg)

        # cleanup logs
        app.closelog()
        applicationLog = app.logfile

    print_msg("%s: Installation %s %s" % (summary, ended, succ), log)

    # check for errors
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

def print_avail_params(easyblock, log):
    """
    Print the available easyconfig parameters, for the given easyblock.
    """
    app = get_class(easyblock, log)
    extra = app.extra_options()
    mapping = easyconfig.convert_to_help(EasyConfig.default_config + extra)

    for key, values in mapping.items():
        print "%s" % key.upper()
        print '-' * len(key)
        for name, value in values:
            tabs = "\t" * (3 - (len(name) + 1) / 8)
            print "%s:%s%s" % (name, tabs, value)

        print


def dep_graph(fn, specs, log):
    """
    Create a dependency graph for the given easyconfigs.
    """

    # check whether module names are unique
    # if so, we can omit versions in the graph 
    names = set()
    for spec in specs:
        names.add(spec['module'][0])
    omit_versions = len(names) == len(specs)

    def mk_node_name(mod):
        if omit_versions:
            return mod[0]
        else:
            return '-'.join(mod)

    # enhance list of specs
    for spec in specs:
        spec['module'] = mk_node_name(spec['module'])
        spec['unresolvedDependencies'] = [mk_node_name(s) for s in spec['unresolvedDependencies']] #[s[0] for s in spec['unresolvedDependencies']]

    # build directed graph
    dgr = digraph()
    dgr.add_nodes([spec['module'] for spec in specs])
    for spec in specs:
        for dep in spec['unresolvedDependencies']:
            dgr.add_edge((spec['module'], dep))

    # write to file
    dottxt = dot.write(dgr)
    if fn.endswith(".dot"):
        # create .dot file
        try:
            f = open(fn, "w")
            f.write(dottxt)
            f.close()
        except IOError, err:
            log.error("Failed to create file %s: %s" % (fn, err))
    else:
        # try and render graph in specified file format
        gvv = gv.readstring(dottxt)
        gv.layout(gvv, 'dot')
        gv.render(gvv, fn.split('.')[-1], fn)

    print "Wrote dependency graph to %s" % fn


if __name__ == "__main__":
    try:
        main()
    except EasyBuildError, e:
        sys.stderr.write('ERROR: %s\n' % e.msg)
        sys.exit(1)
