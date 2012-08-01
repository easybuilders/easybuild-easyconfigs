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
import os, sys, re

from easybuild.tools.build_log import getLog

class PbsJob:
    """Interaction with torque"""

    def __init__(self, script, env_vars, name):
        """
        create a new Job to be submitted to PBS
        """
        self.log = getLog("PBS")
        self.script = script
        self.env_vars = env_vars
        self.name = name

        global pbs
        global PBSQuery
        try:
            from PBSQuery import PBSQuery
            import pbs
        except ImportError:
            self.log.error("Cannot import PBSQuery or pbs. Please make sure pbs_python is installed and usable.")

        self.pbs_server = pbs.pbs_default()
        self.pbsconn = pbs.pbs_connect (self.pbs_server)

        self.jobid = None

    def submit(self):
        """Submit the jobscript txt, set self.jobid"""
        txt = self.script
        self.log.debug("Going to submit script %s" % txt)

        resources = {"walltime": "72:00:00", "nodes": "1:ppn=%s" % self.get_ppn() }

        attropl = pbs.new_attropl(1) ## jobparams
        attropl[0].name = 'Job_Name'
        attropl[0].value = self.name

        tmpattropl = pbs.new_attropl(len(resources)) ## jobparams
        idx = 0
        for k, v in resources.items():
            tmpattropl[idx].name = 'Resource_List' ## resources
            tmpattropl[idx].resource = k
            tmpattropl[idx].value = v
            idx += 1
        attropl.extend(tmpattropl)

        ## add a bunch of variables (added by qsub)
        ## also set PBS_O_WORKDIR to os.getcwd()
        os.environ.setdefault('WORKDIR', os.getcwd())

        defvars = ['MAIL', 'HOME', 'PATH', 'SHELL', 'WORKDIR']
        vars = ["PBS_O_%s=%s" % (x, os.environ.get(x, 'NOTFOUND_%s' % x)) for x in defvars]
        vars.extend(["%s=%s" % (name, value) for (name, value) in self.env_vars.items()])
        tmpattropl = pbs.new_attropl(1)
        tmpattropl[0].name = 'Variable_List'
        tmpattropl[0].value = ",".join(vars)
        attropl.extend(tmpattropl)

        import tempfile
        fh, scriptfn = tempfile.mkstemp()
        f = os.fdopen(fh, 'w')
        self.log.debug("Writing temp jobscript to %s" % scriptfn)
        f.write(txt)
        f.close()

        queue='long'
        self.log.debug("Going to submit to queue %s" % queue)

        extend = 'NULL' ## always
        jobid = pbs.pbs_submit(self.pbsconn, attropl, scriptfn, queue, extend)

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
        """

        state = self.info(types=['job_state', 'exec_host'])

        jid = [x['id'] for x in state]

        jstate = [ x.get('job_state', None) for x in state]

        def get_uniq_hosts(txt, num= -1):
            """txt host1/cpuid+host2/cpuid
                - num: number of nodes to return
            """
            res = []
            for h_c in txt.split('+'):
                h = h_c.split('/')[0]
                if h in res: continue
                res.append(h)
            return res[:num]
        ehosts = [ get_uniq_hosts(x.get('exec_host', '')) for x in state]

        self.log.debug("Jobid  %s jid %s state %s ehosts %s (%s)" % (self.jobid, jid, jstate, ehosts, state))

        joined = zip(jid, jstate, [''.join(x[:1]) for x in ehosts]) ## only use first node (don't use [0], job in Q have empty list; use ''.join to make string)
        temp = "Id %s State %s Node %s"
        if len(joined) == 0:
            msg = "No jobs found."
        elif len(joined) == 1:
            msg = "Found 1 job %s" % (temp % tuple(joined[0]))
        else:
            msg = "Found %s jobs\n" % len(joined)
            for j in joined:
                msg += "    %s\n" % (temp % tuple(j))
        self.log.debug("msg %s" % msg)

        return msg

    def info(self, types=None):
        """Return jobinfo"""
        if type(types) is str:
            types = [types]
        self.log.debug("Return info types %s" % types)

        if types is None:
            jobattr = 'NULL'
        else:
            jobattr = pbs.new_attrl(len(types))
            for idx in range(len(types)):
                jobattr[idx].name = types[idx]

        jobs = pbs.pbs_statjob(self.pbsconn, self.jobid, jobattr, 'NULL')
        if len(jobs) == 0:
            res = [] ## return nothing
            self.log.debug("No job found. Wrong id %s or job finished? Returning %s" % (self.jobid, res))
            return res
        elif len(jobs) == 1:
            self.log.debug("Request for jobid %s returned one result %s" % (self.jobid, jobs))
        else:
            self.log.error("Request for jobid %s returned more then one result %s" % (self.jobid, jobs))

        ## more then one, return value
        res = []
        for j in jobs:
            job_details = dict([ (attrib.name, attrib.value) for attrib in j.attribs ])
            job_details['id'] = j.name ## add id
            res.append(job_details)
        self.log.debug("Found jobinfo %s" % res)
        return res

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

