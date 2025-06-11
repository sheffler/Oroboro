import pytest
from datetime import datetime, timedelta

from src.oroboro.oroboro import Event, ObserverEvent, Timeout, NoReason, Oroboro
from src.oroboro.te import *

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
# TODO: improve the package to operate with datetime objects as well as numbers for time.
# This test is a reminder to think about it.
#
# Test the same alternation pattern as alt0.  This time, apply the values externally to AAK
# and advance time manually.  Also, use datetime and timedelta objects to see system times.
#

def xest_te_alt2_datetime():

    asig = 0
    bsig = 0
    csig = 0

    start = datetime.now()

    def mainfn_alt1(oro):

        print(f"***")
        print(f"*** Beginning test test_alt2_datetime")
        print(f"***")

        def preda(d):
            return asig == 1

        a = Pred(preda)

        def predb(d):
            return bsig == 1

        b = Pred(predb)

        def predc(d):
            return csig == 1

        c = Pred(predc)

        teexpr = (ok + a + b |
                  b + ok + a + c)
        print(f"Pretty Print {teexpr}")

        always(psmplr, teexpr, printmatches=1, printfails=1,
               onmatch=checkmatch, onfail=checkfail)

        # yield Timeout(0)
        yield NoReason()
        


    oro = Oroboro()
    oro.start(mainfn_alt1)

    print(f"***")
    print(f"*** Beginning test test_alt1")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0]
    bvals = [0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0]
    cvals = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 1, 2, 1, 2, 2, 2, 1, 1, 2, 2, 2]

    psmplr = ObserverEvent()

    oro.loop().run_once(10)

    for i in range(12):

        a = avals[i]
        b = bvals[i]
        c = cvals[i]

        # psmplr.post_at()
        delta = timedelta(seconds = ((i+1) * 10))
        t = start + delta

        oro.post_at(t, psmplr)

        oro.loop().run_until(t)

    oro.loop().run_forever()
    
#
# Examine the intersection (^) operator
#   Because the LHS and the RHS are the same, this is like &.
#

def test_te_compound_intersection1():

    asig = 0
    bsig = 0

    start = datetime.now()

    def mainfn_compound_intersection1(oro):

        print(f"***")
        print(f"*** Beginning test test_te_alt_intersection1")
        print(f"***")

        def preda(d):
            return asig == 1

        a = Pred(preda)

        def predb(d):
            return bsig == 1

        b = Pred(predb)

        tex = a + b
        
        teexpr = tex ^ tex

        print(f"Pretty Print {teexpr}")

        always(psmplr, teexpr, printmatches=1, printfails=1, onmatch=checkmatch, onfail=checkfail)

        # yield Timeout(0)
        yield NoReason()
        


    oro = Oroboro()
    oro.start(mainfn_compound_intersection1)

    print(f"***")
    print(f"*** Beginning test test_alt1")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
    bvals = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 1, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    oro.loop().run_once(10)

    for i in range(12):

        asig = avals[i]
        bsig = bvals[i]

        t = (i+1) * 10

        oro.post_at(t, psmplr)

        oro.loop().run_until(t)

    oro.loop().run_forever()
    

#
# An alternate test examining the intersection (^) operator
# There will be one match at cycle 2.
# There will be multiple matches starting at cycle 6, and at cycle 7.
#

def test_te_alt_intersection1():

    asig = 0
    bsig = 0

    start = datetime.now()

    def mainfn_alt_intersection1(oro):

        print(f"***")
        print(f"*** Beginning test test_te_alt_intersection1")
        print(f"***")

        def preda(d):
            return asig == 1

        a = Pred(preda)

        def predb(d):
            return bsig == 1

        b = Pred(predb)

        aa = a | (a + a) | (a + a + a)
        bb = b | (b + b)
        
        teexpr = aa ^ bb

        print(f"Pretty Print {teexpr}")

        always(psmplr, teexpr, printmatches=1, printfails=1, onmatch=checkmatch, onfail=checkfail)

        # yield Timeout(0)
        yield NoReason()
        


    oro = Oroboro()
    oro.start(mainfn_alt_intersection1)

    print(f"***")
    print(f"*** Beginning test test_alt_intersection1")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0]
    bvals = [0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    oro.loop().run_once(10)

    for i in range(12):

        asig = avals[i]
        bsig = bvals[i]

        t = (i+1) * 10

        oro.post_at(t, psmplr)

        oro.loop().run_until(t)

    oro.loop().run_forever()
    
#
# One match at 6, 10, 11.
#

def test_te_compound_intersection_alt1():

    asig = 0
    bsig = 0
    csig = 0

    def mainfn_compound_intersection_alt1(oro):

        print(f"***")
        print(f"*** Beginning test test_te_compound_intersection2")
        print(f"***")

        def preda(d):
            return asig == 1

        a = Pred(preda)

        def predb(d):
            return bsig == 1

        b = Pred(predb)

        def predc(d):
            return csig == 1

        c = Pred(predc)

        ab = a + b
        bc = b + c
        
        teexpr = ab ^ bc

        print(f"Pretty Print {teexpr}")

        always(psmplr, teexpr, printmatches=1, printfails=1, onmatch=checkmatch, onfail=checkfail)

        # yield Timeout(0)
        yield NoReason()
        


    oro = Oroboro()
    oro.start(mainfn_compound_intersection_alt1)

    print(f"***")
    print(f"*** Beginning test test_te_compound_intersection")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0]
    bvals = [0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0]
    cvals = [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 1, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    oro.loop().run_once(10)

    for i in range(15):

        asig = avals[i]
        bsig = bvals[i]
        csig = cvals[i]

        t = (i+1) * 10

        oro.post_at(t, psmplr)

        oro.loop().run_until(t)

    oro.loop().run_forever()
    
