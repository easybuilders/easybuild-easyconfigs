##
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
module for doing parallel builds. This uses a PBS-like cluster. You should be able to submit jobs (which can have
dependencies)

Support for PBS is provided via the PbsJob class. If you want you could create other job classes and use them here.
"""
import math
import os
import re

import easybuild.tools.config as config
from easybuild.framework.easyblock import get_class
from easybuild.tools.pbs_job import PbsJob
from easybuild.tools.config import get_repository

def build_easyconfigs_in_parallel(build_command, easyconfigs, output_dir, log):
    """
    easyconfigs is a list of easyconfigs which can be built (e.g. they have no unresolved dependencies)
    this function will build them in parallel by submitting jobs

    returns the jobs
    """
    log.info("going to build these easyconfigs in parallel: %s", easyconfigs)
    job_module_dict = {}
    # dependencies have already been resolved,
    # so one can linearly walk over the list and use previous job id's
    jobs = []
    for ec in easyconfigs:
        # This is very important, otherwise we might have race conditions
        # e.g. GCC-4.5.3 finds cloog.tar.gz but it was incorrectly downloaded by GCC-4.6.3
        # running this step here, prevents this
        prepare_easyconfig(ec, log)

        # the new job will only depend on already submitted jobs
        log.info("creating job for ec: %s" % str(ec))
        new_job = create_job(build_command, ec, log, output_dir)
        # Sometimes unresolvedDependencies will contain things, not needed to be build.
        job_deps = [job_module_dict[dep] for dep in ec['unresolvedDependencies'] if dep in job_module_dict]
        new_job.add_dependencies(job_deps)
        new_job.submit()
        log.info("job for module %s has been submitted (job id: %s)" % (new_job.module, new_job.jobid))
        # update dictionary
        job_module_dict[new_job.module] = new_job.jobid
        new_job.cleanup()
        jobs.append(new_job)

    return jobs


def create_job(build_command, easyconfig, log, output_dir=""):
    """
    Creates a job, to build a *single* easyconfig
    build_command is a format string in which a full path to an eb file will be substituted
    easyconfig should be in the format as processEasyConfig returns them
    output_dir is an optional path. EASYBUILDTESTOUTPUT will be set inside the job with this variable
    returns the job
    """
    # create command based on build_command template
    command = build_command % easyconfig['spec']

    # capture PYTHONPATH, MODULEPATH and all variables starting with EASYBUILD
    easybuild_vars = {}
    for name in os.environ:
        if name.startswith("EASYBUILD"):
            easybuild_vars[name] = os.environ[name]

    others = ["PYTHONPATH", "MODULEPATH"]

    for env_var in others:
        if env_var in os.environ:
            easybuild_vars[env_var] = os.environ[env_var]

    log.info("Dictionary of environment variables passed to job: %s" % easybuild_vars)

    # create unique name based on module name
    name = "%s-%s" % easyconfig['module']

    var = config.environmentVariables['testOutputPath']
    easybuild_vars[var] = os.path.join(os.path.abspath(output_dir), name)

    # just use latest build stats
    buildstats = get_repository().get_buildstats(*easyconfig['module'])
    resources = {}
    if buildstats:
        previous_time = buildstats[-1]['build_time']
        resources['hours'] = int(math.ceil(previous_time * 2 / 60))

    job = PbsJob(command, name, easybuild_vars, resources=resources)
    job.module = easyconfig['module']

    return job


def get_instance(easyconfig, log):
    """
    Get an instance for this easyconfig
    easyconfig is in the format provided by processEasyConfig
    log is a logger object

    returns an instance of Application (or subclass thereof)
    """
    spec = easyconfig['spec']
    name = easyconfig['module'][0]

    # handle easyconfigs with custom easyblocks
    easyblock = None
    reg = re.compile(r"^\s*easyblock\s*=(.*)$")
    for line in open(spec).readlines():
        match = reg.search(line)
        if match:
            easyblock = eval(match.group(1))
            break

    app_class = get_class(easyblock, log, name=name)
    return app_class(spec, debug=True)


def prepare_easyconfig(ec, log):
    """ prepare for building """
    try:
        instance = get_instance(ec, log)
        instance.fetch_step()
    except:
        pass
