import pytest
from datetime import datetime, timedelta

from src.Oroboro import Event, ObserverEvent, Timeout, NoReason, Oroboro
from src.TE import *

#
# Define an empty cycle.
#

def __ok(d):
    return True

ok = Pred(__ok)


#
# To make these tests self checking, the expected value of the match (1)
# or failure (2) at each cycle is stored in an array mvals.
# A value of 0 means that neither match or failure is expected beginning
# at the cycle.
#

mvals = None                            # matchvals array - set by test

def checkmatch(tup):

    global mvals
    idx = tetrace_scycle(tup) - 1

    if idx < len(mvals):
        expect = mvals[idx]

        print(f"Checking expected match is 1:{expect}")
        assert expect == 1, f"Match expected, got {expect}"


def checkfail(tup):

    global mvals
    idx = tetrace_scycle(tup) - 1

    if idx < len(mvals):
        expect = mvals[idx]

        print(f"Checking expected failure is 2:{expect}")
        assert expect == 2, f"Failure expected, got {expect}"


#
# The example from the README file
#

def test_te_readme_one2():

    asig = 0
    bsig = 0

    start = datetime.now()

    def mainfn_readme_one2(oro):

        print(f"***")
        print(f"*** Beginning test test_te_readme_one2")
        print(f"***")

        def preda(d):
            return asig == 1

        a = Pred(preda)

        te = (a + a) | (a + a + a)
        
        print(f"Pretty Print {te}")

        always(psmplr, te, printmatches=1, printfails=1)
        # onmatch=checkmatch, onfail=checkfail)

        # yield Timeout(0)
        yield NoReason()
        


    oro = Oroboro()
    oro.start(mainfn_readme_one2)

    print(f"***")
    print(f"*** Beginning test test_te_readme_one2")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [1, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    oro.loop().run_once(10)

    for i in range(12):

        asig = avals[i]

        t = (i+1) * 10

        oro.post_at(t, psmplr)

        oro.loop().run_until(t)

    oro.loop().run_forever()
    


