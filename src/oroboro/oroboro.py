#
# An event-driving simulation framework using generators to model tasks.  It provides a cooperative
# multitasking model.
#
# A task executes until it reaches a yield statement.  The arguments to the yield are a list of
# reasons that the task can be resumed.
#
# Example:
#
# def taskfn(arg1, arg2):
#    while true:
#        dothis(arg1)
#        dothat(arg2)
#        yield Timeout(20), WaitEvent(evt)
#
# t = Task(taskfn, arg1, arg2)
#
# The above defines and launches a task.  When the task reaches the yield statement, flow of control
# will be returned to the Oroboro scheduler.  The task will "reawaken" after either 20 time units, or
# the post of the event "evt" ... whichever occurs first.
#
# A task may determine for what reason it was reawaked by using the functions
#    currentreason()
#    currentreasonindex()
#
# (c) 2004-2025
#

from .loop import BaseLoop

import string
import types
import sys
import traceback


# Debugging flags
_traceon = 1
_singlestepping = 0

# Logging functions
def log_info(s):
    print(f"INFO {s}")

def log_warning(s):
    print(f"WARN {s}")

def log_error(s):
    print(f"ERR {s}")

def log_critical(s):
    print(f"CRIT {s}")


#
# task states
#
[BORN, RUNNING, WAITING, EXITED, KILLED] = range(5)

#
# Module global variables
#
loop = None
__currenttask = None                    # current task
__currentreason = None                  # which reason is active
__maxtaskwid = 4                        # max width of task names

#
# User uses this to find out current time
#
def currenttime():

    """This returns the current simulation time as a long.
    """
    
    global loop
    if loop:
        return loop.now
    else:
        return -1

def _setcurrenttask(t):
    global __currenttask
    __currenttask = t

#
# User uses this to find out current task
#
def currenttask():

    """This function is used to reference the current task object
    within a running task.
    """
    
    global __currenttask
    return __currenttask

def currentsystf():

    """Within a running task, this function will return a reference to the
    apvm.systf object that is the root of this Oroboro session.
    """

    global __currenttask
    return __currenttask.systf

def _setcurrentreason(r):
    global __currentreason
    __currentreason = r

#
# User uses these to determine current reason and
# index of reason in yield tuple.
#
def currentreason():

    """Upon resuming after a yield, this returns a reference to the
    reason that was triggered.
    """

    global __currentreason
    return __currentreason

def currentreasonindex():

    """Upon resuming after a yield, this returns the index of the triggering
    reason in the yield clause list.
    """
    
    global __currentreason
    return __currentreason.index

#
# Keep running max width of task names for message formatting
#
def _calctaskwid(tsk):
    global __maxtaskwid
    wid = len(tsk.name)
    if wid > __maxtaskwid:
        __maxtaskwid = wid
    

    
#
# A task yields on a reason or reasons.  This helper function
# accepts a reason, tuple of reasons, or list of reasons,
# checks the types and turns into a list of reasons.
#

def _listifyreasons(xx):

    import types

    if type(xx) == tuple:
        ll = list(xx)
    elif type(xx) == list:
        ll = xx
    else:
        ll = [ xx ]

    for l in ll:
        if not isinstance(l, Reason):
            raise "Must yield with a reason or list of reasons.  Object given is: %s" % str(l)

    return ll

#
# Print a message for the current task
#

def taskmsg(msg):

    """The user may use this function within a task to print a nicely
    formatted message with the current simulation time and a task
    identifier.
    """
    
    tim = currenttime()
    tsk = currenttask()
    tid = tsk.id
    wid = __maxtaskwid

    log_info("%10d [%6d %*s]:%s" % (tim, tid, wid,
                                      tsk.name, msg))
    

#
# Print a nice "trace" message that can be turned on or off
#  - these are used for scheduler stuff usually
#

def tracemsg(msg):

    """Used internally by Oroboro to format and print execution tracing
    messages.
    """

    global _traceon
    if _traceon:
        tim = currenttime()
        tsk = currenttask()
        tid = tsk.id
        wid = __maxtaskwid

        log_info("%10d [%6d %*s]:  <%s>" % (tim, tid, wid,
                                              tsk.name, msg))

def traceon():
    """Turn on trace messages."""
    global _traceon
    _traceon = 1

def traceoff():
    """Turn off trace messages."""
    global _traceon
    _traceon = 0


#
# An event is an Oro object that has a list of listeners that want
# to know when the event is posted.
#
# There are two potential policies for handling "post."
#  - a post call immediately invokes the waiters
#  - a post is handled by a 0-delay callback
#
# Oroboro currently implements the first policy for evaluation.
#

class Event:

    eventid = 1

    # Methods:
    
    def __init__(self, nicename=""):

        self.waiters = { }
        self.val = None
        self.nicename = nicename
        self.count = 0

        self.id = Event.eventid
        Event.eventid += 1

        tracemsg("Event: %d created" % self.id)

    def __repr__(self):

        return "<Event %d>" % self.id

    #
    # Notify waiters that want to hear about this event.
    #
    def post(self, val=None):

        tracemsg("Post: %s Val: %s Count: %d" % (str(self), str(val), self.count))

        self.count = self.count +1
        self.val = val
        # TOM: 2025
        # for w in self.waiters.keys():
        wcopy = self.waiters.copy()
        for w in wcopy.keys():
            w()

    #
    # Ask to be notified about this event.
    #
    def addwaiter(self, w):
        if w not in self.waiters:
            self.waiters[w] = None
        
    #
    # Remove the waiter from the notification list.
    #
    def removewaiter(self, w):
        del self.waiters[w]


#
# An Observer Event is handled specially.  It is placed in the observer list and handled
# at the end of the time step.
#

class ObserverEvent(Event):
    pass

#
# This is the real workhorse.  A task is a wrapper around a generator function
# that yields with a list of reasons to be resumed.
#
class Task:

    taskid = 1

    def __init__(self, fn, *args):

        assert(fn)

        self.g = None                   # generator function - after started
        self.fn = fn                    # generator function
        self.args = args                # startup args
        # self.name = ""                # useful for debugging (future use)
        try:
            self.name = fn.__name__     # fns and methods have __name__
        except:
            self.name = ""
        _calctaskwid(self)              # update max width of task names

        self.id = Task.taskid
        Task.taskid += 1

        self.parent = currenttask()     # another task
        self.systf = currentsystf()     # an APVM systf instance
        self.status = BORN
        self.result = 0                 # final value of task, if any
        
        # when a task yields this holds a copy
        self.reasons = [ ]

        # if other tasks want status change information, they wait to be notified
        self.waiters = { }

        # schedule the initial callback that gets this task going
        self.kickoff()

    def __repr__(self):

        return "<Task %d>" % self.id

    #
    # Schedule the #0 delay callback that starts a new task.
    #
    def kickoff(self):

        self.khandle = loop.call_now(self.kicker, 0, None, 0, None)

    #
    # This is the callback that creates the generator for the task.
    #
    def kicker(self, time, value, index, userdata):

        tracemsg("Kicker! " + str(self))

        self.khandle = None             # GC
        # self.g = apply(self.fn, self.args) # create generator
        self.g = self.fn(*self.args)    # create generator

        # This test ensures that user has provided a generator
        if type(self.g) != types.GeneratorType:
            print("*** OROBORO ERROR ***")
            raise "Argument to task() must be a GeneratorType"
        
        self.runstep()                  # run to first yield
        

    #
    # Wake up this task because a particular reason has fired.
    # - cancel the other reasons
    # - set record of which reason is current one
    # - reasons should be indicated by type and object
    #
    def runstep(self):

        if not self.g:                  # if not scheduled, can't run it
            print(self.fn, self.args, self.g)
            raise "Task %s not started!" % str(self)

        prevtask = currenttask()        # restore when done
        _setcurrenttask(self)           # set global task identifier

        tracemsg("Runstep")

        for r in self.reasons:
            r.cancel_it()               # cancel old reasons
        self.reasons = [ ]              # GC list

        # advance our generator and obtain next reasons
        try:
            self.status = RUNNING
            tracemsg("Stepping Generator")
            rr = next(self.g)

            while isinstance(rr, NoReason):
                # null reason implementation
                rr = next(self.g)

            self.reasons = _listifyreasons(rr)
            tracemsg("Yield on %s" %
                     ",".join(map(lambda x: str(x), self.reasons)))
            
            self.status = WAITING

        # generator exits
        except StopIteration:

            # task has ended - notify waiters on status change
            self.status = EXITED
            tracemsg("Exiting")
            _setcurrenttask(prevtask)   # on exception, still need to do
            self.endtask()
            self.g = None               # GC generator
            return

        # task has other uncaught exception
        except:

            sys.stdout.flush()
            sys.stderr.write("*** Python Exception Encountered ***\n")

            # Print the traceback
            traceback.print_exc()
            if self.systf.exitonexcept:
                sys.stderr.write("*** Oroboro Exiting - exit(1) ***\n")
                sys.exit(1)


        # Enumerate, assign ids, schedule
        for i in range(len(self.reasons)):
            r = self.reasons[i]
            r.index = i
            r.schedule_it()

        _setcurrenttask(prevtask)

        tracemsg("End of Runstep")

        # pause for user CR if single stepping for debugging
        if _singlestepping:
            sys.stdin.readline()


    def kill(self):

        """Kill this task by cancelling all of its reasons.
        """

        prevtask = currenttask()
        _setcurrenttask(self)

        tracemsg("Killing Myself")

        for r in self.reasons:
            r.cancel_it()
        self.reasons = [ ]
        self.status = KILLED
        # notify waiters of status change
        _setcurrenttask(prevtask)
        self.endtask()


    #
    # If other tasks want status change notifications they wait on this.
    # This first implementation of Oro will chain right to them.
    #
    def endtask(self):
        # a waiter is a callable method of a reason
        # TOM: 2025 - operate on the copy because the waiters are removed as executed
        # TOM: 2025 - this probably used to work before for/in implemented some sort of fast iteration ...
        # for w in self.waiters.keys():
        wcopy = self.waiters.copy()
        for w in wcopy.keys():
            w()
            
    def addwaiter(self, w):
        if w not in self.waiters:
            self.waiters[w] = None

    def removewaiter(self, w):
        del self.waiters[w]

        

    
#
# This is the base class for all reasons.
#
# A bare reason has no associated object, only a task waiting
# on it.  It is not to be used directly.
#
class Reason:

    def __init__(self):

        self.task = currenttask()
        self.cancelled = None

        # Reasons are assigned an index when put into a list and yielded on
        self.index = 0

    def __str__(self):

        return "<Reason>"

    def schedule_it(self):

        if self.cancelled:
            raise "Cannot re-use cancelled reason: %s" % str(self)

        tracemsg("Schedule %s" % self)
        self.cancelled = None

    def cancel_it(self):

        tracemsg("Cancel %s" % self)
        self.cancelled = 1
        self.task = None

    def do_it(self):

        tracemsg("Do %s" % self)

        if self.cancelled:
            return

        prevreason = currentreason()
        _setcurrentreason(self)
        self.task.runstep()
        _setcurrentreason(prevreason)

#
# No reason is a way to form a generator for the oroboro scheduler
# that does not result in a callback.  It is an alternative to
# the use of
#   yield timeout(0)
#

class NoReason(Reason):

    pass


#
# Wait for a timeout callback.  Requesting this schedules a VPI callback.
#
class Timeout(Reason):

    def __init__(self, interval):

        # test that interval is a long
        self.interval = interval
        Reason.__init__(self)

    def __str__(self):

        return "<Timeout %d>" % self.interval

    def schedule_it(self):

        Reason.schedule_it(self)

        self.handle = loop.call_later(self.interval, self.callback, None, 0, None)

    def cancel_it(self):

       # Allow these to transpire and then cancel in Python
        Reason.cancel_it(self)

    def callback(self, value, index, userdata):

        # TOM2025: loop will keep track of this
        # _setcurrenttime(_vpi_time_to_long(time))

        if self.cancelled:

            tracemsg("Timeout quietly ignored")
            return

        Reason.do_it(self)
        
#
# To wait on an event.
#
class WaitEvent(Reason):

    def __init__(self, ev):

        # test that ev is an event
        if not isinstance(ev, Event):
            raise "Can only wait on an event.  Object given is: %s" % str(ev)

        self.ev = ev
        Reason.__init__(self)

    def __str__(self):

        return "<Wait %s>" % self.ev

    def schedule_it(self):

        self.ev.addwaiter(self.do_it)
        Reason.schedule_it(self)

    def cancel_it(self):

        self.ev.removewaiter(self.do_it)
        Reason.cancel_it(self)

#
# To wait on the status change of a task
#
class Status(Reason):

    def __init__(self, t):

        # test that t is a task
        if not isinstance(t, Task):
            raise "Can only wait on status change of a task.  Object given is: %s" % str(t)

        self.t = t
        Reason.__init__(self)

    def __str__(self):

        return "<Status %s>" % self.t

    def schedule_it(self):

        self.t.addwaiter(self.do_it)
        Reason.schedule_it(self)

    def cancel_it(self):

        self.t.removewaiter(self.do_it)
        Reason.cancel_it(self)


#
# The root task is something that is the parent of all tasks and
# never dies (because it is never really running).  It appears
# to be running at all times, however.
#
class _roottask:

    def __init__(self, oro):

        self.g = None
        self.name = "ROOT"
        self.id = 0
        self.parent = None
        self.systf = oro
        self.status = RUNNING

        _setcurrenttask(self)
        tracemsg("IN ROOT")

    def __str__(self):

        return "<ROOTTASK>"

    def runstep(self):

        return


        
#
# The main oroboro application is small.
#
class Oroboro():

    def __init__(self, exitonexcept=True):

        self.exitonexcept = exitonexcept
        global loop
        loop = BaseLoop()

    def loop(self):
        global loop
        return loop


    # This is the instantiation of an oroboro scheduler
    #  TOM: the old one looked up the name of the main function from a cmd line arg,
    #  and the name of the python module containing it from the modulename.
    #  Now, we can simply accept the mainfn as an arg.  It is the coroutine
    #  and we should learn how to use async/await on it
    #
    #  userfn - is the main generator
    def start(self, userfn):

        log_info("*** Oroboro ***")

        # Create a "fake" root task so that the user task has a parent
        _roottask(self)

        # Start user's main function as a task with APVM systf instance arg
        t = Task(userfn, self)

        return int(t.result)

    #
    # Run the loop until a specific time
    #
    def run_until(self, t):
        global loop
        return loop.run_until(t)

    #
    # Run the loop until it is empty
    #
    def run_forever(self):
        global loop
        return loop.run_forever()
    #
    # POST - signal an event as soon as possible
    #   The event is put in the scheduled queue and next loop eval will find it
    #
    def post(self, ev):
        assert isinstance(ev, Event)

        if isinstance(Event, ObserverEvent):
            loop.call_observer_now(ev.post)
        else:
            loop.call_now(ev.post)
        

    #
    # POST_AT - signal an event at a specific time
    #
    def post_at(self, t, ev):
        assert isinstance(ev, Event)

        if isinstance(Event, ObserverEvent):
            loop.call_observer_at(t, ev.post)
        else:
            loop.call_at(t, ev.post)
    
