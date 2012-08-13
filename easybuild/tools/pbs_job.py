##
# Copyright 2012 Stijn De Weirdt, Toon Willems
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
Interface module to TORQUE (PBS).
"""

import os

from easybuild.tools.build_log import getLog

MAX_WALLTIME = 72

class PbsJob:
    """Interaction with TORQUE"""

    def __init__(self, script, name, env_vars=None, resources={}):
        """
        create a new Job to be submitted to PBS
        env_vars is a dictionary with key-value pairs of environment variables that should be passed on to the job
        resources is a dictionary with optional keys: ['hours', 'cores'] both of these should be integer values.
        hours can be 1 - MAX_WALLTIME, cores depends on which cluster it is being run.
        """
        self.log = getLog("PBS")
        self.script = script
        if env_vars:
            self.env_vars = env_vars.copy()
        else:
            self.env_vars = {}
        self.name = name

        global pbs
        global PBSQuery
        try:
            from PBSQuery import PBSQuery
            import pbs
        except ImportError:
            self.log.error("Cannot import PBSQuery or pbs. Please make sure pbs_python is installed and usable.")

        try:
            self.pbs_server = pbs.pbs_default()
            self.pbsconn = pbs.pbs_connect(self.pbs_server)
        except:
            self.log.error("Could not connect to the default pbs server, is this correctly configured?")

        # setup the resources requested

        # validate requested resources!
        hours = resources.get('hours', MAX_WALLTIME)
        if hours > MAX_WALLTIME:
            self.log.warn("Specified %s hours, but this is impossible. (resetting to %s hours)" % (hours, MAX_WALLTIME))
            hours = MAX_WALLTIME

        max_cores = self.get_ppn()
        cores = resources.get('cores', max_cores)
        if cores > max_cores:
            self.log.warn("number of requested cores (%s) was greater than available (%s) " % (cores, max_cores))
            cores = max_cores

        # only allow cores and hours for now.
        self.resources = {
                          "walltime": "%s:00:00" % hours,
                          "nodes": "1:ppn=%s" % cores
                         }
        # set queue based on the hours requested
        if hours >= 12:
            self.queue = 'long'
        else:
            self.queue = 'short'
        self.jobid = None
        self.deps = []

    def add_dependencies(self, job_ids):
        """
        Add dependencies to this job.
        job_ids is an array of job ids (e.g.: 8453.master2.gengar....)
        if only one job_id is provided this function will also work
        """
        if isinstance(job_ids, str):
            job_ids = list(job_ids)

        self.deps.extend(job_ids)

    def submit(self):
        """Submit the jobscript txt, set self.jobid"""
        txt = self.script
        self.log.debug("Going to submit script %s" % txt)


        # Build default pbs_attributes list
        pbs_attributes = pbs.new_attropl(1)
        pbs_attributes[0].name = 'Job_Name'
        pbs_attributes[0].value = self.name


        # set resource requirements
        resourse_attributes = pbs.new_attropl(len(self.resources))
        idx = 0
        for k, v in self.resources.items():
            resourse_attributes[idx].name = 'Resource_List'
            resourse_attributes[idx].resource = k
            resourse_attributes[idx].value = v
            idx += 1
        pbs_attributes.extend(resourse_attributes)

        # add job dependencies to attributes
        if self.deps:
            deps_attributes = pbs.new_attropl(1)
            deps_attributes[0].name = pbs.ATTR_depend
            deps_attributes[0].value = ",".join(["afterok:%s" % dep for dep in self.deps])
            pbs_attributes.extend(deps_attributes)

        ## add a bunch of variables (added by qsub)
        ## also set PBS_O_WORKDIR to os.getcwd()
        os.environ.setdefault('WORKDIR', os.getcwd())

        defvars = ['MAIL', 'HOME', 'PATH', 'SHELL', 'WORKDIR']
        pbsvars = ["PBS_O_%s=%s" % (x, os.environ.get(x, 'NOTFOUND_%s' % x)) for x in defvars]
        # extend PBS variables with specified variables
        pbsvars.extend(["%s=%s" % (name, value) for (name, value) in self.env_vars.items()])
        variable_attributes = pbs.new_attropl(1)
        variable_attributes[0].name = 'Variable_List'
        variable_attributes[0].value = ",".join(pbsvars)

        pbs_attributes.extend(variable_attributes)

        import tempfile
        fh, scriptfn = tempfile.mkstemp()
        f = os.fdopen(fh, 'w')
        self.log.debug("Writing temporary job script to %s" % scriptfn)
        f.write(txt)
        f.close()

        self.log.debug("Going to submit to queue %s" % self.queue)

        # extend paramater should be 'NULL' because this is required by the python api
        extend = 'NULL'
        jobid = pbs.pbs_submit(self.pbsconn, pbs_attributes, scriptfn, self.queue, extend)

        is_error, errormsg = pbs.error()
        if is_error:
            self.log.error("Failed to submit job script %s: error %s" % (scriptfn, errormsg))
        else:
            self.log.debug("Succesful jobsubmission returned jobid %s" % jobid)
            self.jobid = jobid
            os.remove(scriptfn)

    def state(self):
        """
        Return the state of the job
        State can be 'not submitted', 'running', 'queued' or 'finished',
        """
        state = self.info(types=['job_state', 'exec_host'])

        if state == None:
            if self.jobid == None:
                return 'not submitted'
            else:
                return 'finished'

        jid = state['id']

        jstate = state.get('job_state', None)

        def get_uniq_hosts(txt, num=-1):
            """
            - txt: format: host1/cpuid+host2/cpuid
            - num: number of nodes to return (default: all)
            """
            res = []
            for h_c in txt.split('+'):
                h = h_c.split('/')[0]
                if h in res:
                    continue
                res.append(h)
            return res[:num]

        ehosts = get_uniq_hosts(state.get('exec_host', ''), 1)

        self.log.debug("Jobid %s jid %s state %s ehosts %s (%s)" % (self.jobid, jid, jstate, ehosts, state))
        if jstate == 'Q':
            return 'queued'
        else:
            return 'running'

    def info(self, types=None):
        """
        Return jobinfo
        """
        if not self.jobid:
            self.log.debug("no jobid, job is not submitted yet?")
            return None

        # convert single type into list
        if type(types) is str:
            types = [types]

        self.log.debug("Return info types %s" % types)

        # create attribute list to query pbs with
        if types is None:
            jobattr = 'NULL'
        else:
            jobattr = pbs.new_attrl(len(types))
            for idx, attr in enumerate(types):
                jobattr[idx].name = attr


        # get a new connection (otherwise this seems to fail)
        pbs.pbs_disconnect(self.pbsconn)
        self.pbsconn = pbs.pbs_connect(self.pbs_server)
        jobs = pbs.pbs_statjob(self.pbsconn, self.jobid, jobattr, 'NULL')
        if len(jobs) == 0:
            # no job found, return None info
            res = None
            self.log.debug("No job found. Wrong id %s or job finished? Returning %s" % (self.jobid, res))
            return res
        elif len(jobs) == 1:
            self.log.debug("Request for jobid %s returned one result %s" % (self.jobid, jobs))
        else:
            self.log.error("Request for jobid %s returned more then one result %s" % (self.jobid, jobs))

        # only expect to have a list with one element
        j = jobs[0]
        # convert attribs into useable dict
        job_details = dict([ (attrib.name, attrib.value) for attrib in j.attribs ])
        # manually set 'id' attribute
        job_details['id'] = j.name
        self.log.debug("Found jobinfo %s" % job_details)
        return job_details

    def remove(self):
        """Remove the job with id jobid"""
        result = pbs.pbs_deljob(self.pbsconn, self.jobid, '') ## use empty string, not NULL
        if result:
            self.log.error("Failed to delete job %s: error %s" % (self.jobid, result))
        else:
            self.log.debug("Succesfully deleted job %s" % self.jobid)

    def get_ppn(self):
        """Guess the ppn for full node"""
        pq = PBSQuery()
        node_vals = pq.getnodes().values() ## only the values, not the names
        interesni_nodes = ('free', 'job-exclusive',)
        res = {}
        for np in [int(x['np'][0]) for x in node_vals if x['state'][0] in interesni_nodes]:
            res.setdefault(np, 0)
            res[np] += 1

        ## return most frequent
        freq_count, freq_np = max([(j, i) for i, j in res.items()])
        self.log.debug("Found most frequent np %s (%s times) in interesni nodes %s" % (freq_np, freq_count, interesni_nodes))

        return freq_np

