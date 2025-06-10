#
# Temporal Expressions are structured tasks that "return" multiple
# values.  Each "value" returned by a TE (a match)
# is signaled by the TE task posting an event to its parent.
# A TE signals that it has no more matches by exiting.  Its final
# value indicates how many matches were made during its lifetime, or
# if no matches were successful, a failure trace is returned.
#
#
# Copyright (c) 2004-2025 Tom Sheffler
#
#    This source code is free software; you can redistribute it
#    and/or modify it in source code form under the terms of the GNU
#    General Public License as published by the Free Software
#    Foundation; either version 2 of the License, or (at your option)
#    any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA
#

from src.Oroboro import Task, Timeout, Event, WaitEvent, Status, currenttime, currenttask, currentreason, currentreasonindex
import types
import pprint

#
# ToDo: define mechanism to handle error
#

def error(s):
    "Print an error.  Potentially take corrective action"
    print(s)

#
# The te base class
#

class TE:

    def __init__(self):

        self.op = "x"                   # op symbol
        self.opname = ""                # name
        self.smpl = None                # sampling event

        # TEs have at most two children
        self.a = None
        self.b = None

    def __str__(self):

        """Return the pretty-printed parse tree"""

        return pprint.pformat(self.parserepr())

    def __repr__(self):
        return "<@%s>" % self.op
        

    def parserepr(self):

        """Return something that can be pretty printed."""

        if isinstance(self.a, TE):
            a = self.a.parserepr()
        else:
            a = self.a

        if isinstance(self.b, TE):
            b = self.b.parserepr()
        else:
            b = self.b

        return (self.op, a, b)


    def run(self, pe, d):

        """All TEs implement the run method.  This is the task that generates
        the matches.  The "pe" arg is the parent event that this TE
        uses to indicate matches.  The "d" arg is the dictionary sent
        to the TE."""

        pass

    #
    # Operator overloading on temporal expressions
    #

    # a+b
    def __add__(self, x):
        return Cat(self, x)

    # a/b
    def __div__(self, x):
        return Fuse(self, x)

    # a|b
    def __or__(self, x):
        return Alt(self, x)

    # a&b
    def __and__(self, x):
        return Conj(self, x)

    # a^b
    def __xor__(self, x):
        return Intersect(self, x)

    # a>>b
    def __rshift__(self, x):
        return Cond(self, x)

    # a>b
    def __gt__(self, x):
        return CondFuse(self, x)

    # ~a
    def __invert__(self):
        return Inv(self)

    # a*(n,m)
    def __mul__(self, x):
        return Repeat(self, x)


#
# A TE task can track its children and kill them recursively.
#

class TETask(Task):

    def __init__(self, fn, *args):

        # add a new field (list for now - dict later)
        self.subs = { }
        self.sube = Event("tetask")    # if child has change in status

        Task.__init__(self, fn, *args)

    def hassubtasks(self):
        return len(self.subs) != 0

    def nosubtasks(self):
        return len(self.subs) == 0

    # Watch subtasks and remove from set when they die.
    def monitor(self, t):
        yield Status(t)
        # print "TETASK MONITOR"
        del self.subs[t]                # remove from tracked list
        self.sube.post(t)               # signal listeners of status change

    # Spawn a new task, and track under this task
    def subtask(self, fn, *args):
        t = TETask(fn, *args)
        tm = Task(self.monitor, t)
        self.subs[t] = None             # add to set of children
        return t

    # Kill this task and all subchildren recursively
    def killsubs(self):
        for sb in self.subs:
            sb.killsubs()
        self.subs = { }
        self.kill()

#
# sample(sampler, te)
#   attach the sampler to TE
#

def sample(ssampler, tte):

    # if no sampler yet attached
    if tte.smpl == None:

        tte.smpl = ssampler

        # recursively attach to children

        if isinstance(tte.a, TE):
            sample(ssampler, tte.a)

        if isinstance(tte.b, TE):
            sample(ssampler, tte.b)

    return tte


#
# pred
#  Users define predicate functions.
#  The pred accepts a single dict argument.
#

class Pred(TE):

    def __init__(self, p):

        TE.__init__(self)

        try:
            self.op = p.__name__        # name of fn
        except:
            self.opname = "pred"
        self.opname = "pred"
        self.a = p

    def run(self, pe, d):

        me = currenttask()
        me.name = "@" + self.op         # change task name for tracing

        stime = currenttime()           # starting sim time
        ssmpl = self.smpl.count         # starting sample count
        matchcount = 0

        # evaluate predicate with fresh copy of dict for user fn
        d = d.copy()
        x = self.a(d)

        if x:
            tup = (matchcount, self, d,
                   ssmpl, ssmpl, stime, stime,
                   ())
            pe.post(tup)                # signal a match
            matchcount = matchcount + 1

        yield Timeout(0)

        # TOM: I had experimented with implementing noreason, but it
        # does not give the desired effect.  When used w/ roSynch policy,
        # it caused spawned TE tasks fail to run because spawning a task
        # in a roSynch region is not permitted.
        #
        # Removed for now, use timeout(0), even though there is no
        # reason to go thru the scheduler again.  TEs run during rwSynch.
        # yield noreason()

        # set termination trace
        tup = (matchcount, self, d, ssmpl, ssmpl, stime, stime, ())
        me.val = tup
        return

#
# inv
#  consume all events of child.
#  if no matches, emit one match
#  if there are matches, fail
#

class Inv(TE):

    def __init__(self, a):

        TE.__init__(self)

        self.op = "inv"
        self.opname = "inv"
        self.a = a
        self.smpl = None

    def run(self, pe, d):

        me = currenttask()
        me.name = "@" + self.op       # change task name for tracing
        ae = Event("inv")

        at = me.subtask(self.a.run, ae, d) # new task anchored at NOW

        aval = None
        afail = None

        stime = currenttime()           # starting sim time
        ssmpl = self.smpl.count         # starting sample count
        matchcount = 0

        while not me.nosubtasks():

            yield WaitEvent(ae), WaitEvent(me.sube)

            if currentreasonindex() == 0:
                # Since success/failure inverted, we save the trace
                # of a match as the failure trace.
                aval = ae.val
                matchcount = matchcount + 1

            if currentreasonindex() == 1:
                deadtask = me.sube.val
                afail = deadtask.val

        # Invert - if no matches, signal one match.  If there are matches,
        # do not signal any matches.
        if matchcount == 0:

            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (afail,))
            pe.post(tup)
            

        # return/failure trace - inverted
        if matchcount == 0:
            # success
            tup = (1, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            # failure
            tup = (0, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (aval,))

        me.val = tup
        return



#
# a;b
#  also implements fusion, cond and cond-fusion.
#

class Cat(TE):

    # args a and be are TEs as well
    def __init__(self, a, b):

        TE.__init__(self)

        self.op = "+"
        self.opname = "cat"
        self.a = a                      # parse structure args
        self.b = b
        self.smpl = None                # sample event
        self.fusion = None
        self.cond = None

    # start this TE a running as a tetask
    def run(self, pe, d):               # pe is per-match parent evt

        me = currenttask()
        me.name = "@" + self.op       # change task name for tracing
        ae = Event("cat")
        be = Event("catb")

        at = me.subtask(self.a.run, ae, d) # new task anchored at NOW

        aval = None                     # for failure trace
        bval = None

        stime = currenttime()           # starting sim time
        ssmpl = self.smpl.count         # starting sample count
        matchcount = 0
        amatchcount = 0                 # for use if this is a->b 

        while not me.nosubtasks():

            # wait on ae or other subtasks change in status
            yield WaitEvent(ae), WaitEvent(be), WaitEvent(me.sube)

            if currentreasonindex() == 0:
                d = ae.val[2]
                bt = me.subtask(self.runb, be, d, ssmpl, stime, ae.val)
                amatchcount = amatchcount + 1

            if currentreasonindex() == 1:
                d = be.val[2]
                tup = (matchcount,) + be.val[1:]
                pe.post(tup)
                matchcount = matchcount + 1

            if currentreasonindex() == 2:
                deadtask = me.sube.val
                if deadtask == at:
                    aval = deadtask.val
                else:
                    bval = deadtask.val


        # if a>>b, we match if a does not
        if self.cond:
            if amatchcount == 0:
                # a did not match, signal a match
                tup = (matchcount, self, d,
                       ssmpl, self.smpl.count, stime, currenttime(),
                       (aval,))
                pe.post(tup)
                matchcount = matchcount + 1


        # compute return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            if bval:
                children = (aval,) + bval[7]
            else:
                children = (aval,)

            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   children)

        me.val = tup
        # print "CAT EXIT", tup
        return


    def runb(self, pe, d, ssmpl, stime, aeval):

        me = currenttask()
        me.name = "@" + self.op       # change task name for tracing
        be = Event("catbb")

        bval = None

        if not self.fusion:
            yield WaitEvent(self.smpl)

        bt = me.subtask(self.b.run, be, d)

        matchcount = 0                  # not meaningful for only b part ...

        # only one subtask, but simple pattern here
        while not me.nosubtasks():
   
            yield WaitEvent(be), WaitEvent(me.sube)

            if currentreasonindex() == 0:
                d = be.val[2]
                tup = (matchcount, self, d,
                       ssmpl, self.smpl.count,
                       stime, currenttime(), (aeval, be.val))
                matchcount = matchcount + 1
                pe.post(tup)

            if currentreasonindex() == 1:
                deadtask = me.sube.val
                bval = deadtask.val

        # set termination trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (bval,))

        me.val = tup
        return

#
# a/b
#   - does not insert sampling event between a and b
#

class Fuse(Cat):

    def __init__(self, a, b):

        Cat.__init__(self, a, b)

        self.op = "/"
        self.opname = "fuse"
        self.fusion = 1
    

#
# a>>b
#   - match if a does not
#     else, matches where b matches
#

class Cond(Cat):

    def __init__(self, a, b):

        Cat.__init__(self, a, b)

        self.op = ">>"
        self.opname = "cond"
        self.fusion = None
        self.cond = 1
    

#
# a>b (fusion variant of cond)
#   - match if a does not
#     else, matches where b matches
#

class CondFuse(Cat):

    def __init__(self, a, b):

        Cat.__init__(self, a, b)

        self.op = ">"
        self.opname = "cond"
        self.fusion = 1
        self.cond = 1
    

#
# a | b
#

class Alt(TE):

    def __init__(self, a, b):

        TE.__init__(self)

        self.op = "|"
        self.opname = "alt"
        self.a = a
        self.b = b

        assert isinstance(a, TE)
        assert isinstance(b, TE)

    def run(self, pe, d):

        assert isinstance(self.smpl, Event)

        me = currenttask()
        me.name = "@" + self.op         # change task name for tracing
        ae = Event("alta")
        be = Event("altb")

        at = me.subtask(self.a.run, ae, d)
        bt = me.subtask(self.b.run, be, d)

        aval = None                     # for failure trace
        bval = None

        ssmpl = self.smpl.count
        stime = currenttime()
        matchcount = 0

        while me.hassubtasks():

            yield WaitEvent(ae), WaitEvent(be), WaitEvent(me.sube)

            if currentreasonindex() == 0:
                tup = (matchcount, self, ae.val[2],
                       ssmpl, self.smpl.count, stime, currenttime(),
                       (ae.val,))
                pe.post(tup)
                matchcount = matchcount + 1

            if currentreasonindex() == 1:
                tup = (matchcount, self, be.val[2],
                       ssmpl, self.smpl.count, stime, currenttime(),
                       (be.val,))
                pe.post(tup)
                matchcount = matchcount + 1

            if currentreasonindex() == 2:
                deadtask = me.sube.val
                if deadtask == at:
                    aval = deadtask.val
                else:
                    bval = deadtask.val


        # compute return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (0, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (aval, bval))

        me.val = tup
        return

#
# Helper function: merge two dictionaries, producing a new copy.
#
def _dmerge(d1, d2):
    d = d1.copy()
    for k in d2:
        d[k] = d2[k]
    return d


#
# a & b - at the same end time
#  does not currently produce multiple matches at same time step
#

class Conj(TE):

    def __init__(self, a, b):

        TE.__init__(self)

        self.op = "&"
        self.opname = "conj"
        self.a = a
        self.b = b
        self.smpl = None

        assert isinstance(a, TE)
        assert isinstance(b, TE)

    def run(self, pe, d):

        assert isinstance(self.smpl, Event)

        me = currenttask()
        me.name = "@" + self.op       # change task name for tracing

        ae = Event()
        be = Event()

        at = me.subtask(self.a.run, ae, d)
        bt = me.subtask(self.b.run, be, d)

        aval = None
        bval = None

        ssmpl = self.smpl.count
        stime = currenttime()
        matchcount = 0

        # record the last completion time of a/b: (esmpls, etime)
        lasta = (-1, -1)
        lastb = (-1, -1)

        while me.hassubtasks():

            yield WaitEvent(ae), WaitEvent(be), WaitEvent(me.sube)

            if currentreasonindex() == 0:

                lasta = (self.smpl.count, currenttime())

                if (lasta[0] == lastb[0]):

                    d1 = be.val[2]
                    d2 = ae.val[2]

                    tup = (matchcount, self, _dmerge(d1, d2),
                           ssmpl, self.smpl.count, stime, currenttime(),
                           (ae.val, be.val))
                    pe.post(tup)
                    matchcount = matchcount + 1

            if currentreasonindex() == 1:

                lastb = (self.smpl.count, currenttime())

                if (lasta[0] == lastb[0]):

                    d1 = ae.val[2]
                    d2 = be.val[2]

                    tup = (matchcount, self, _dmerge(d1, d2),
                           ssmpl, self.smpl.count, stime, currenttime(),
                           (ae.val, be.val))
                    pe.post(tup)
                    matchcount = matchcount + 1


            if currentreasonindex() == 2:
                deadtask = me.sube.val
                if deadtask == at:
                    aval = deadtask.val
                else:
                    bval = deadtask.val
                    

        # return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (0, self, d, 
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (aval, bval))
                   
        me.val = tup
        return


#
# This operator defines the intersection.
#  a^b
#

class Intersect(TE):

    def __init__(self, a, b):

        TE.__init__(self)

        self.op = "^"
        self.opname = "intersect"
        self.a = a
        self.b = b
        self.smpl = None

        assert isinstance(a, TE)
        assert isinstance(b, TE)

    def run(self, pe, d):

        assert isinstance(self.smpl, Event)

        me = currenttask()
        me.name = "@" + self.op       # change task name for tracing
        ae = Event()
        be = Event()

        at = me.subtask(self.a.run, ae, d)
        bt = me.subtask(self.b.run, be, d)

        aval = None
        bval = None

        ssmpl = self.smpl.count
        stime = currenttime()
        matchcount = 0

        # record of completions
        aevals = [ ]
        bevals = [ ]

        while me.hassubtasks():

            yield WaitEvent(ae), WaitEvent(be), WaitEvent(me.sube)

            if currentreasonindex() == 0:

                for beval in bevals:

                    d1 = beval[2]
                    d2 = ae.val[2]

                    tup = (matchcount, self, _dmerge(d1, d2),
                           ssmpl, self.smpl.count, stime, currenttime(),
                           (ae.val, beval))
                    pe.post(tup)
                    matchcount = matchcount + 1

                aevals.append(ae.val)

            if currentreasonindex() == 1:

                for aeval in aevals:

                    d1 = aeval[2]
                    d2 = be.val[2]

                    tup = (matchcount, self, _dmerge(d1, d2),
                           ssmpl, self.smpl.count, stime, currenttime(),
                           (aeval, be.val))
                    pe.post(tup)
                    matchcount = matchcount + 1

                bevals.append(be.val)

            if currentreasonindex() == 2:
                deadtask = me.sube.val
                if deadtask == at:
                    aval = deadtask.val
                else:
                    bval = deadtask.val

        # return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (0, self, d, 
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (aval, bval))
                   
        me.val = tup
        return


#
# repeat a * (n,m)
#   or   a * n
#

class Repeat(TE):

    def __init__(self, a, x):

        TE.__init__(self)

        self.op = "repeat"
        self.opname = "repeat"
        self.a = a

        if type(x) == int:
            self.n = x
            self.m = x

        elif type(x) == tuple:
            self.n = x[0]
            self.m = x[1]

        else:
            raise "Repeat arg must be int or tuple."

        assert (isinstance(self.a, TE))
        assert (self.n >= 0)
        assert (self.m >= self.n)

    #
    # i - iteration count
    # atrace - tuple of traces of successes [1..i-1]

    def arunner(self, i, atrace, pe, d):

        me = currenttask()
        me.name = "@" + self.op + str(i) # change task name for tracing
        ae = Event("arunner")

        stime = currenttime()
        ssmpl = self.smpl.count
        matchcount = 0

        assert(i >= 1)

        # print "REPEAT ATRACE", atrace

        if i != 1:
            yield WaitEvent(self.smpl) # all others preceded by clock

        at = me.subtask(self.a.run, ae, d)
        aval = None

        # wait for match and/or end of subtask
        while at:
            yield WaitEvent(ae), Status(at)

            # this succeeds with its count, and the normal tuple stuff
            if currentreasonindex() == 0:

                # this tuple is the match trace for i
                # and the prefix trace for i+1
                trace = atrace + (ae.val,)
                
                tup = (i, trace, (matchcount, self, ae.val[2],
                                  ssmpl, self.smpl.count, stime, currenttime(),
                                  trace))

                # print "REPEAT ae", i, tup

                matchcount = matchcount + 1
                pe.post(tup)

            if currentreasonindex() == 1:

                aval = at.val
                at = None

        # set termination trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   atrace + (aval,))

        me.val = tup
        return


    
    def run(self, pe, d):

        me = currenttask()
        me.name = "@" + self.op         # change task name for tracing
        ae = Event("repeat")            # fires each time an a succeeds

        aval = None

        stime = currenttime()
        ssmpl = self.smpl.count
        i = 0
        matchcount = 0

        # emit a*0
        if self.n == 0:
            tup = (matchcount, self, d, ssmpl, ssmpl, stime, stime, ())
            matchcount = matchcount + 1
            pe.post(tup)

        # spawn first match with a
        at = me.subtask(self.arunner, 1, (), ae, d)

        while me.hassubtasks():
            
            yield WaitEvent(ae), WaitEvent(me.sube)

            if currentreasonindex() == 0:
                # match for iteration number i 
                (i, trace, atup) = ae.val

                if i >= self.n and i <= self.m:

                    # if this match in desired range, signal a match
                    tup = (matchcount, self, atup[2],
                           ssmpl, self.smpl.count, stime, currenttime(),
                           trace)

                    matchcount = matchcount + 1
                    pe.post(tup)

                if i < self.m:
                    # spawn i+1
                    at = me.subtask(self.arunner, i+1, trace, ae, d)

            if currentreasonindex() == 1:
                deadtask = me.sube.val
                aval = deadtask.val

        # set termination trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            # 'arunner' children are children for fail
            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   aval[7])

        me.val = tup
        return


################################################################
#
# FILTERS
#
################################################################

#
# firstof
#  after first match, kill all subtasks and return
#

class Firstof(TE):

    def __init__(self, a):
        
        TE.__init__(self)

        self.op = "firstof"
        self.opname = "firstof"
        self.a = a
        self.smpl = None

    def run(self, pe, d):

        me = currenttask()
        me.name = "@" + self.op
        ae = event("firstof")

        at = me.subtask(self.a.run, ae, d)

        aval = None

        stime = currenttime()
        ssmpl = self.smpl.count
        matchcount = 0

        while not me.nosubtasks():

            yield WaitEvent(ae), WaitEvent(me.sube)

            if currentreaosonindex() == 0:

                aval = ae.val
                matchcount = matchcount + 1

                # kill all remaining subtasks
                me.killsubs()

            if currentreasonindex() == 1:
                pass

        # compute return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (aval,))

        me.val = tup
        return



#
# once per time step
#

class Once(TE):

    def __init__(self, a):
        
        TE.__init__(self)

        self.op = "once"
        self.opname = "once"
        self.a = a
        self.smpl = None

        self.fired = None


    def clear(self):
        # yield vpireason(apvm.cbNextSimTime)
        yield Timeout(0)
        self.fired = None
        

    def run(self, pe, d):

        me = currenttask()
        me.name = "@" + self.op
        ae = Event("once")

        at = me.subtask(self.a.run, ae, d)

        stime = currenttime()
        ssmpl = self.smpl.count
        matchcount = 0

        while not me.nosubtasks():

            yield WaitEvent(ae), WaitEvent(me.sube)

            if currentreasonindex() == 0:

                if not self.fired:
                    # propagate this one
                    pe.post(ae.val)
                    matchcount = matchcount + 1
                    self.fired = 1
                    # clear fired at next sim time
                    x = me.subtask(self.clear)

            if currentreasonindex() == 1:
                deadval = me.sube.val


        # compute return/failure trace
        if matchcount != 0:
            tup = (matchcount, self, {},
                   ssmpl, self.smpl.count, stime, currenttime(),
                   ())
        else:
            tup = (matchcount, self, d,
                   ssmpl, self.smpl.count, stime, currenttime(),
                   (deadval,))

        me.val = tup
        return



################################################################
#
# Print a TE Trace
#
# TEs return a tuple of information that is useful for debugging.
#  op (ssmpl/esmpl) (stime/etime) matchcount { dict }
#    child1
#    child2
#
################################################################

def tetrace_print(tup, indent=0):

    # print "XX", tup

    leader = " " * indent
    fmt = "%s%s (%d/%d) (%d/%d) %d %s"
    fmt2 = "%s%s"

    if type(tup) == tuple:

        (matchcount, node, dict, ssmpl, esmpl, stime, etime, children) = tup

        x = fmt % (leader, node.op, ssmpl, esmpl, stime, etime, matchcount, str(dict))
        print(x)
        for c in children:
            tetrace_print(c, indent + 2)
    else:
        x = fmt2 % (leader, str(tup))
        print(x)


################################################################
#
# TE TRACE DISSECTION FUNCTIONS
#
################################################################

def tetrace_dict(tup):
    return tup[2]

def tetrace_count(tup):
    return tup[0]

def tetrace_scycle(tup):
    return tup[3]

def tetrace_ecycle(tup):
    return tup[4]

def tetrace_stime(tup):
    return tup[5]

def tetrace_etime(tup):
    return tup[6]

def tetrace_children(tup):
    return tup[7]


################################################################
#
# TOP LEVEL CONSTRUCTS
#
################################################################

#
# Helper task for forevery, always, never, teevent.
#

def xalways(smplr, teexpr, e, printmatches, printfails, onmatch, onfail):

    me = currenttask()

    while 1:

        yield WaitEvent(smplr), WaitEvent(e), WaitEvent(me.sube)

        if currentreasonindex() == 0:
            # spawn another te at this sample point
            t = me.subtask(teexpr.run, e, { })

        if currentreasonindex() == 1:
            if printmatches:
                print("MATCH")
                tetrace_print(e.val)

            if onmatch:
                onmatch(e.val)

        if currentreasonindex() == 2:

            # failure is an exit with no matches
            if tetrace_count(me.sube.val.val) == 0:

                if printfails:
                    print("FAILURE")
                    tetrace_print(me.sube.val.val)

                if onfail:
                    onfail(me.sube.val.val)

    

def always(smplr, teexpr, e=None, printmatches=0, printfails=0, onmatch=None, onfail=-1):

    assert(isinstance(smplr, Event))
    assert(isinstance(teexpr, TE))

    ev = e
    if ev == None:
        ev = Event("always")            # private event

    def always_error(tup):
        error("Temporal expression always assertion failed.")

    if onfail == -1:
        onfail=always_error

    # attach if not already
    sample(smplr, teexpr)

    t = TETask(xalways, smplr, teexpr, ev, printmatches, printfails, onmatch, onfail)
    return t

# 'forevery' synonym for always
forevery = always


def never(smplr, teexpr, e=None, printmatches=0, printfails=0):

    ev = e
    if ev == None:
        ev = Event("never")             # private event

    def never_error(tup):
        error("Temporal expression never assertion matched.")

    # attach if not already
    sample(smplr, teexpr)

    t = TETask(xalways, smplr, teexpr, ev, printmatches, printfails, never_error, None)
    return t


#
# This function produces an event that is signalled whenever the te matches.
# Use it like a normal event.
#
#   e = teevent(pos, pred(preda) + pred(predb))
#

def teevent(smplr, teexpr, printmatches=0, printfails=0):

    # create a new event
    ev = Event("teevent")

    # attach if not already
    sample(smplr, teexpr)

    # start the temporal expression running
    t = TETask(xalways, smplr, teexpr, ev, printmatches, printfails, None, None)

    # return the event
    return ev


#
# Helper task for teeval
#

def xteeval(smplr, teexpr, e):

    me = currenttask()

    yield WaitEvent(smpl)

    t = me.subtask(teexpr.run, e, { })

    while 1:

        yield WaitEvent(smpl), waitevent(e), waitevent(me.sube)

        if currentreasonindex() == 0:
            pass

        if currentreasonindex() == 1:
            print("MATCH")
            tetrace_print(e.val)

        if currentreasonindex() == 2:
            print("FAILURE")
            tetrace_print(me.sube.val.val)


#
# Evaluate the expr starting at the next sample point
#

def teeval(smplr, teexpr, e=None):

    if e == None:
        e = Event("teeval")
    t = tetask(xteeval, smplr, teexpr, e)
    return t



    
