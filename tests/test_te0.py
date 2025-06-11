#
# This file defines a family of self-checking tests of the temporal
# expression package.  Each test is data-driven by arrays 'avals', 'bvals'
# a 'cvals', which are driven onto signals 'asig', 'bsig' and 'csig'.
#
# The expected match or failure state is stored in array.  These values
# are used to make the tests self-checking.
#

import pytest

from src.oroboro.oroboro import Event, ObserverEvent, Timeout, Oroboro
from src.oroboro.te import *


#
# Explanation of MATCH and FAILURE
#
# Log Files will show MATCHES and FAILURES in a pretty-printed format.  For example, in test alt0,
# there is a match that begins at cycle 2 and ends at cycle 4.
#
# MATCH
# | (2/4) (20/40) 0 {}
#   + (2/4) (20/40) 0 {}
#     + (2/3) (20/30) 0 {}
#       __ok (2/2) (20/20) 0 {}
#       preda (3/3) (30/30) 0 {}
#     predb (4/4) (40/40) 0 {}
#
# This says:
# The alternation operator matched from cycle to to cycle four (time 20 to time 40), composed of
#   - the concatenation operator from cycle 2 to cycle 4, consisting of
#     - the concatenation operator from cycle 2 to 3, consisting of
#       - the OK assertion at cycle 2
#       - the PREDA predicate at cycle 3
#     - the PREDB predicate at cycle 4
#
# FAILURE is similar, but the trace gives an example of how the expression could not be satisfied.
#
# FAILURE
# | (1/2) (10/20) 0 {}
#   + (1/2) (10/20) 0 {}
#     + (1/2) (10/20) 0 {}
#       __ok (1/1) (10/10) 1 {}
#       preda (2/2) (20/20) 0 {}
#   + (1/1) (10/10) 0 {}
#     + (1/1) (10/10) 0 {}
#       + (1/1) (10/10) 0 {}
#         predb (1/1) (10/10) 0 {}
#
# This indicates that the assertion beginning at cycle 1 failed at cycle 2.
# Both sides of the alternation operator (|) failed.
# The sequence (ok + PREDA) failed at cycle 2 (because A was not a 1)
# The sequence (PREDB + ...) failed at cycle 1 (because B was not a 1)
#



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
# Simple alternation test
#
#  teexpr = ok + a + b | b + ok + a + c
#

def mainfn_alt0(oro):

    print(f"***")
    print(f"*** Beginning test test_alt0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0]
    bvals = [0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0]
    cvals = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 1, 2, 1, 2, 2, 2, 1, 1, 2, 2, 2]

    psmplr = ObserverEvent()

    a = 0
    b = 0
    c = 0

    def preda(d):
        return a == 1

    def predb(d):
        return b == 1

    def predc(d):
        return c == 1

    #
    # Define the temporal expression and print it
    #
    teexpr = (ok + Pred(preda) + Pred(predb) |
              Pred(predb) + ok + Pred(preda) + Pred(predc))
    print(f"Pretty Print {teexpr}")

    #
    # Assert the temporal expression at each cycle of the psmplr event
    #
    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    #
    # Run the stimulus trace
    #
    for i in range(12):

        yield Timeout(10)
        
        a = avals[i]
        b = bvals[i]
        c = cvals[i]

        # psmplr.post()
        oro.post(psmplr)

    return

#
# Test alternation and verify the results.  Use AAK Tasks to schedule setting the values
#

def test_te_alt0():

    oro = Oroboro()
    oro.start(mainfn_alt0)

    oro.loop().run_forever()
    
    return

#
# Test the same alternation pattern as alt0.  This time, apply the values externally to AAK
# and advance time manually.  This is more similar to the way AAK would be used in an Agent context.
#

def test_te_alt1():

    a = 0
    b = 0
    c = 0

    def mainfn_alt1(oro):

        print(f"***")
        print(f"*** Beginning test test_alt0")
        print(f"***")

        def preda(d):
            return a == 1

        def predb(d):
            return b == 1

        def predc(d):
            return c == 1

        teexpr = (ok + Pred(preda) + Pred(predb) |
                  Pred(predb) + ok + Pred(preda) + Pred(predc))
        print(f"Pretty Print {teexpr}")

        always(psmplr, teexpr, printmatches=1, printfails=1,
               onmatch=checkmatch, onfail=checkfail)

        yield Timeout(0)


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
        t = (i+1) * 10
        oro.post_at(t, psmplr)

        oro.run_until(t)

    oro.loop().run_forever()
    
    
    
#
# Simple conjunction test
#
#  teexpr = (ok + a + b + ok)  &  (b + ok + a + c)
#
# match at 2 detected at 5
# match at 8 detected at 11
# interesting failure at 9 detected at 12
# 
#

def mainfn_conj0(oro):

    print(f"***")
    print(f"*** Beginning test test_conj0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0]
    bvals = [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0]
    cvals = [0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0
    csig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    def predc(d):
        return csig == 1

    c = Pred(predc)

    teexpr = (ok + a + b + ok) & (b + ok + a + c)
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(12):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]
        csig = cvals[i]

        oro.post(psmplr)

    return

def test_te_conj0():

    oro = Oroboro()
    oro.start(mainfn_conj0)

    oro.loop().run_forever()
    
    return


#
# Conjunction test with variable length operands.
#
#  teexpr = (a + (ok * (1,8))) & ((ok * (1,8)) + b)
#
# Recall that both sides of & must start and end at the same cycle
# for a match to succeed.  This pattern finds a followed by b after
# 1 to 8 cycles.
#

def mainfn_conj1(oro):

    print(f"***")
    print(f"*** Beginning test test_conj1")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    bvals = [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 2, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    teexpr = (a + (ok * (1,8))) & ((ok * (1,8)) + b)
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(12):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]

        # psmplr.post()
        oro.post(psmplr)
        
    return


def test_te_conj1():

    oro = Oroboro()
    oro.start(mainfn_conj1)

    oro.loop().run_forever()
    
    return
    

#
# repeat test
#
#  teexpr = ((ok+a) | b) * (2,3)
#
# If you run this test, you can look at the output log and examine the
# traces of the matches to see how multiple matches at the same end time
# were found by the expression.
#

def mainfn_repeat0(oro):

    print(f"***")
    print(f"*** Beginning test test_repeat0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0]
    bvals = [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0]

    # expected vals on the completion cycle
    global mvals
    mvals = [1, 2, 2, 2, 1, 1, 1, 1, 2, 2, 2, 2, 1, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0

    def preda(d):
        d['a'] = currenttask().id
        return asig == 1

    def predb(d):
        d['b'] = currenttask().id       
        return bsig == 1

    teexpr = ((ok + Pred(preda)) | Pred(predb)) * (2,3)
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
          onmatch=checkmatch, onfail=checkfail)

    for i in range(16):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]

        # psmplr.post()
        oro.post(psmplr)

    return

def test_te_repeat0():
    
    oro = Oroboro()
    oro.start(mainfn_repeat0)

    oro.loop().run_forever()
    
    return
    

#
# Test expression
#    a + ok * (3,7) + b
# to find a pair of markers separated by an interval.
#
# match at 2 succeeds
# match at 7 succeeds twice
# failure starting at 10 is detected at 18
#

def mainfn_repeat1(oro):

    print(f"***")
    print(f"*** Beginning test test_repeat1")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
    avals = [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    bvals = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]

    # expected vals on the completion cycle
    global mvals
    mvals = [2, 1, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    teexpr = a + (ok * (3,7)) + b
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(20):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]

        # psmplr.post()
        oro.post(psmplr)

    return

def test_te_repeat1():
    
    oro = Oroboro()
    oro.start(mainfn_repeat1)

    oro.loop().run_forever()
    
    return
    

#
# Simple intersection test, with dictionaries
#
#  teexpr = a ^ (ok * (2,5) + b)
#
# match at 3 detected at 6 and 7
# match at 9 detected at 13 and 14 (an not 15)
# 
#

def mainfn_int0(oro):

    print(f"***")
    print(f"*** Beginning test test_int0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    bvals = [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0]
    cvals = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 2, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0
    csig = 0

    def preda(d):
        d['a'] = csig
        return asig == 1

    a = Pred(preda)

    def predb(d):
        d['b'] = csig
        return bsig == 1

    b = Pred(predb)

    teexpr = a ^ (ok*(2,5) + b)
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(16):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]
        csig = cvals[i]

        # psmplr.post()
        oro.post(psmplr)
    

    return
def test_te_int0():
    
    oro = Oroboro()
    oro.start(mainfn_int0)

    oro.loop().run_forever()
    
    return
    

#
# Simple conditional test
#   a >> b+b+b
#
# match starting at 3 is interesting
# failure starting at 9 is interesting
#

def mainfn_cond0(oro):

    print(f"***")
    print(f"*** Beginning test test_cond0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    bvals = [0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0
    csig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    teexpr = a >> (b+b+b)
    print(f"Pretty Print {teexpr}")

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(16):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]

        # psmplr.post()
        oro.post(psmplr)
                      

    return

def test_te_cond0():

    oro = Oroboro()
    oro.start(mainfn_cond0)

    oro.loop().run_forever()


#
# Simple once test.
#   once(a+a | b+b | c+c)
#
#

def mainfn_once0(oro):

    print(f"***")
    print(f"*** Beginning test test_once0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    bvals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    cvals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [2, 2, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0
    csig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    def predc(d):
        return csig == 1

    c = Pred(predc)

    teexpr = Once((a+a) | (b+b) | (c+c))
    # If you rerun the test with the expr below, you will see same matches,
    # but multiple of them at each success.
    #
    # teexpr = ((a+a) | (b+b) | (c+c))
    print("Pretty Print", teexpr)

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(16):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]
        csig = cvals[i]

        # psmplr.post()
        oro.post(psmplr)
                      
    return

def test_te_once0():

    oro = Oroboro()
    oro.start(mainfn_once0)

    oro.loop().run_forever()
    

#
# Simple inv test.
# Same stimuli as test_once0, but inverted match.
#
#

def mainfn_inv0(oro):

    print(f"***")
    print(f"*** Beginning test test_inv0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
    avals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    bvals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    cvals = [0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0]

    # set expected match results at each cycle
    global mvals
#   mvals = [2, 2, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2]  # from once0
    mvals = [1, 1, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0
    csig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    def predc(d):
        return csig == 1

    c = Pred(predc)

    teexpr = ~((a+a) | (b+b) | (c+c))
    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(16):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]
        csig = cvals[i]

        # psmplr.post()
        oro.post(psmplr)

    return

def test_te_inv0():

    oro = Oroboro()
    oro.start(mainfn_inv0)

    oro.loop().run_forever()

#
# Simple conditional test
#   req >> ok + ok + ack
#
# match starting at 3
# failure starting at 9 
# failure starting at 12
#

def mainfn_reqack0(oro):

    print(f"***")
    print(f"*** Beginning test test_reqack0")
    print(f"***")

    # cycle= 1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17
    avals = [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]
    bvals = [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]

    # set expected match results at each cycle
    global mvals
    mvals = [1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1]

    psmplr = ObserverEvent()

    asig = 0
    bsig = 0

    def preda(d):
        return asig == 1

    a = Pred(preda)

    def predb(d):
        return bsig == 1

    b = Pred(predb)

    # teexpr = a >> (ok + ok + b)
    teexpr = a >> (~b + ~b + b)
    print(f"Pretty Print {teexpr}")

    always(psmplr, teexpr, printmatches=1, printfails=1,
           onmatch=checkmatch, onfail=checkfail)

    for i in range(17):

        yield Timeout(10)
        
        asig = avals[i]
        bsig = bvals[i]

        # psmplr.post()
        oro.post(psmplr)
                      

    return

    
def test_te_reqack0():

    oro = Oroboro()
    oro.start(mainfn_reqack0)

    oro.loop().run_forever()
