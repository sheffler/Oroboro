#
# Basic implementation of a scheduling loop with a stratified event execution order.
# For each time step, the events are popped from the queue and evaluated.  The evaluation of
# events may add further processing events at the same step with the call_now() method.
#
# Observer events are deferred until the end of the time step at which point they are evaluated.
# Observer events are intended to be used for state checkers and assertion evaluation.  The actions
# of an Observer event should not add new events to the event queue.
#
# (c) 2025
#



import heapq

#
# A Handle holds something in the event queue.
#   - if a Handle is cancelled, it is not executed
#


class Handle:

    handleCounter = 0           # a unique id is given to each handle

    def __init__(self, when, callback, args, loop):

        self.callback = callback
        self.args = args
        self.loop = loop

        self._cancelled = False

        self.when = when

        self.id = Handle.handleCounter
        Handle.handleCounter += 1

    def _run(self):
        try:
            return self.callback(*self.args)
        except (SystemExit, KeyboardInterrupt):
            raise
        # except:
        #    print(f"Error: Handle")

    def cancel(self):
        self._cancelled = True

    def __repr__(self):
        return f"Handle:{self.when} {self.id}  {self.callback.__name__} {self.callback} args:{self.args}"


    def __hash__(self):
        return hash((self.when, self.id))

    #
    # Comparison functions
    #

    def __lt__(self, other):
        if isinstance(other, Handle):
            return self.when < other.when
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Handle):
            return self.when <= other.when
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Handle):
            return self.when > other.when
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Handle):
            return self.when >= other.when
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Handle):
            return (self.when == other.when and
                    self.callback == other.callback and
                    self.args == other.args and
                    self.cancelled == other.cancelled)
        return NotImplemented


#
# An Observer is handled specially at the end of a time tick
#
class ObserverHandle(Handle):

    def __repr__(self):
        return f"ObserverHandle:{self.when} {self.id}  {self.callback.__name__} {self.callback} args:{self.args}"



#
# A little run loop using a heapq to sort handles
#
        
class BaseLoop:

    def __init__(self):

        self.now = 0;             # current time in the loop
        
        self.scheduled = [ ]    # scheduled events
        self.ready = [ ]        # ready events
        self.observers = [ ]    # events handled at the end of the time step

        self.debug = True

    def call_at(self, when, callback, *args):
        "Put a scheduled handle in the queue at the time specified"

        h = Handle(when, callback, args, self)
        heapq.heappush(self.scheduled, h)
        return h

    def call_later(self, delay, callback, *args):
        "Put a scheduled handle in the queue at the relative time specified"

        return self.call_at(self.now+delay, callback, *args)

    # Unused for now
    def call_observer_at(self, when, callback, *args):
        "Put a scheduled handle in the queue at the time specified"

        h = ObserverHandle(when, callback, args, self)
        heapq.heappush(self.scheduled, h)
        return h

    # Unused for now
    def call_observer_later(self, delay, callback, *args):
        "Put a scheduled handle in the queue at the relative time specified"

        return self.call_observer_at(self.now+delay, callback, *args)

    def call_now(self, callback, *args):
        "Ask the scheduler to evaluate a callback at the current time step"

        h = Handle(self.now, callback, args, self)
        self.ready.append(h)
        return h

    def call_observer_now(self, callback, *args):
        "Ask the scheduler to evaluate a callback at the current time step"

        h = ObserverHandle(self.now, callback, args, self)
        self.ready.append(h)
        return h

    def next_when(self):
        "Return the time of the earliest scheduled handle"

        if self.ready:
            return self.now

        if self.scheduled:
            return self.scheduled[0].when
        else:
            return None

    def run_once(self, endtime):
        """Run one iteration of the simulator.  For each ready event at the front
        of the queue less than the target time, evaluate it.
        """

        if self.debug:
            print(f"BaseLoop: running handles at {endtime}")

        # self.ready.clear()      # it should already be empty.  It might not however, because external call_now calls could populate ready

        while self.scheduled:

            handle = self.scheduled[0]
            if (handle.when > endtime):
                # are past the end time
                break

            # adjust the current time            
            self.now = handle.when

            # Possibly make monotonic
            # if handle.when > self.now:
            #     self.now = handle.when

            handle = heapq.heappop(self.scheduled)
            self.ready.append(handle)
            del handle

        # Now run all of the ready handles.  Evaluation of ready handles may add more
        # handles to the ready queue and that is ok.  But let's break them into waves

        while self.ready:       # while there are ready elements

            if self.debug:
                print(f"BaseLoop when:{self.now} has {len(self.ready)} elements")

            # move to staging area
            wave = self.ready
            self.ready = [ ]

            if self.debug:
                print(f"BaseLoop: running WAVE")

            # execute each in this wave
            for h in wave:
                if not h._cancelled:
                    if isinstance(h, ObserverHandle):
                        self.observers.append(h)
                    else:
                        h._run()
            

        # Now run all of the deferred observers at the end of the time step

        owave = self.observers
        self.observers = [ ]
        for h in owave:
            if not h._cancelled:
                h._run()

        # Advance time
        self.now = endtime

        if self.debug:
            print(f"RUN ONCE FINISHED")

    def run_forever(self):

        if self.debug:
            print(f"RUN_FOREVER")
            self.dump()

        while True:
            nexttime = self.next_when()

            if nexttime == None:
                if self.debug:
                    print(f"NO NEXTTIME")
                break

            if self.debug:
                print(f"BaseLoop nexttime:{nexttime}")

            self.run_once(nexttime)

        if self.debug:
            print(f"BaseLoop FINISHED")

    def run_until(self, endtime):

        if self.debug:
            print(f"RUN_UNTIL")
            self.dump()

        while True:
            nexttime = self.next_when()

            if nexttime == None:
                if self.debug:
                    print(f"NO NEXTTIME")
                break

            if nexttime > endtime:
                break

            self.run_once(nexttime)

        if self.debug:
            print(f"BaseLoop RUN_UNTIL FINISHED")

    def dump(self):

        print(f"LOOP heap:{self.scheduled}")
        print(f"LOOP ready:{self.ready}")
