#
# The foundation of the toolkit is the event loop.
#


import pytest

from src.oroboro.loop import BaseLoop


def test_loop_basic():
    "the loop can run a callback"

    loop = BaseLoop()

    val = 0

    def cb0(x):
        nonlocal val
        val = x

    # schedule changing val to 99 at time 10
    loop.call_at(10, cb0, 99)

    assert(val == 0)

    loop.run_once(10)

    assert(val == 99)


def test_loop_basic_sequence():
    "the loop can execute a series of events"

    loop = BaseLoop()

    val = 0

    def cb0(x):
        nonlocal val
        val = x

    # schedule changing val to 99 at time 10
    loop.call_at(10, cb0, 99)
    loop.call_at(20, cb0, 101)
    loop.call_at(30, cb0, 103)

    assert(val == 0)

    loop.run_once(10)

    assert(val == 99)

    loop.run_once(20)

    assert(val == 101)

    loop.run_once(30)

    assert(val == 103)

    
def test_loop_trace():
    "the loop schedules observers after other events"

    loop = BaseLoop()

    trace = [ ]
    expected = ['a', 'checka', 'b', 'checkb']

    def puttrace(x):
        nonlocal trace
        trace.append(x)

    loop.call_at(10, puttrace, 'a')
    loop.call_observer_at(10, puttrace, 'checka')

    loop.call_at(20, puttrace, 'b')
    loop.call_observer_at(20, puttrace, 'checkb')

    loop.run_forever()

    assert(trace == expected)
    
def test_loop_trace_b():
    "the loop schedules observers after other events"

    loop = BaseLoop()

    trace = [ ]
    expected = ['a', 'checka', 'b', 'checkb']

    def puttrace(x):
        nonlocal trace
        trace.append(x)

    loop.call_observer_at(10, puttrace, 'checka')
    loop.call_at(10, puttrace, 'a')

    loop.call_observer_at(20, puttrace, 'checkb')
    loop.call_at(20, puttrace, 'b')

    loop.run_forever()

    assert(trace == expected)
    
    
def test_loop_until():
    "test loop runs up to and including the event time given"

    
    loop = BaseLoop()

    val = 0

    def cb0(x):
        nonlocal val
        val = x

    # schedule changing val to 99 at time 10
    loop.call_at(10, cb0, 99)
    loop.call_at(20, cb0, 101)
    loop.call_at(30, cb0, 103)
    loop.call_at(40, cb0, 105)
    loop.call_at(50, cb0, 107)

    assert(val == 0)

    loop.run_until(30)

    assert(val == 103)

    loop.run_until(40)

    assert(val == 105)
