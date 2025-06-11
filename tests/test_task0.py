#
# Tasks are an abstraction over event loop callbacks in which a generator models
# a sequential execution of steps over time.  Each yield hands control back to the
# scheduler which suspends the task until one of the reasons of its yield becomes true.
#
# The tests in this file verify that Tasks can simulate the passing of time, that they can
# wait for multiple reasons, that events can be posted, and that the scheduler can be executed
# in a variety of ways.


import pytest

from src.oroboro.oroboro import Task, Timeout, Event, WaitEvent, Status, Oroboro, loop, currenttime, currenttask, currentreason, currentreasonindex


def test_tasks_basic_one():
    "create a task and check its side effects at different times as it uses Timeouts"

    val = 0

    # the main task
    def maintask1(oro):
        nonlocal val

        print(f"This is at time 0")

        yield Timeout(10)
        print(f"This is at time 10")
        val = 101
        
        yield Timeout(10)
        print(f"This is at time 20")
        val = 103

        yield Timeout(10)
        print(f"This is at time 30")
        val = 105

        return
    

    # the start of the test body
    oro = Oroboro()

    print("HERE")
    oro.start(maintask1)

    oro.run_until(20)

    assert(val == 103)

    oro.run_forever()

    assert(val == 105)


# Demonstrate yielding for multiple reasons and determining why we were resumed

def test_tasks_basic_timeout_and_event():
    "create a task that yields on both a timeout and an event"

    trace = [ ]                 # trace of reason index
    expected = [0, 1]           # Timeout, then the Event

    def maintask2(oro):
        nonlocal trace

        print(f"This is at time 0")

        yield Timeout(20), WaitEvent(evt)

        print(f"Woke for {currentreason()} at {currenttime()}")
        trace.append(currentreasonindex()) # should have resumed for reason #0

        yield Timeout(20), WaitEvent(evt)

        print(f"Woke for {currentreason()} at {currenttime()}")
        trace.append(currentreasonindex()) # should have resumed for reason #1
    
    # the start of the test body
    oro = Oroboro()

    oro.start(maintask2)

    evt = Event()               # be sure to create after an Oroboro is started
    oro.post_at(30, evt)        # schedule an event to be posted

    oro.run_forever()

    assert(trace == expected)

    
# The following tests involve a main function (mainfn2) calling a sub-task (subr2) in various
# ways and checking the execution trace.

trace = [ ]

def subr2():

    yield Timeout(1)
    print(f"This is time 21")
    trace.append(21)

    yield Timeout(1)
    print(f"This is time 22")
    trace.append(22)

    yield Timeout(1)
    print(f"This is time 23")
    trace.append(23)

    return
    
    
def mainfn2(oro):
    print(f"This is at time 0")

    yield Timeout(10)
    print(f"This is at time 10")
    trace.append(10)

    yield Timeout(10)
    print(f"This is at time 20")
    trace.append(20)

    task2 = Task(subr2)
    val = yield Status(task2)
    print(f"VAL IS {val}")

    yield Timeout(10)
    print(f"This is at time 30")
    trace.append(30)

    return
    
def test_tasks_subtask1():
    "Spawn a maintask that waits for a sub task"

    global trace
    trace = [ ]

    oro = Oroboro()

    oro.start(mainfn2)

    # oro.loop().run_forever()
    oro.run_forever()

    assert(trace == [10, 20, 21, 22, 23, 30])

# See if Run Until works correctly with tasks
def test_tasks_subtask2():
    "Spawn a maintask that waits for a sub task and execute in pieces"

    global trace
    trace = [ ]

    oro = Oroboro()
    oro.start(mainfn2)

    # oro.loop().run_until(22)
    oro.run_until(22)

    assert(trace == [10, 20, 21, 22])

    # oro.loop().run_until(40)
    oro.run_until(40)

    assert(trace == [10, 20, 21, 22, 23, 30])
