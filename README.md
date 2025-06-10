# Oroboro - Event Driven Temporal Expressions

This project implements executable temporal expressions.  The temporal expression language is a powerful notation for asserting statements over sequences of events.  For example, the following expression

    req >> ~ack + ack
    
asserts that if there is a request, there must not be an acknowlegdement one cycle later, and then there must be an acknowledgement one cycle after that.

Oroboro temporal expressions operate with the notion of a "sampling event" that defines when each cycle occurs.  Predicates can examine the Python state space to define the presence of a condition, such as what constitutes  a "request" or "acknowlegement" in the brief example above.


The original APVM/Oroboro project (c 2004) (https://github.com/sheffler/oro-dev) integrated Python and Verilog by using Python generators as coroutines that were co-simulated with Verilog.  Descendents of APVM/Oroboro included PyHVL (https://sourceforge.net/projects/pyhvl/) and eventually CocoTb.  One of the offshoots of the original project was a Temporal Expression package that implemented many of the operators of PSL (property specification language) as Python coroutines.  Temporal expressions simulated alongside a DUT (Device Under Test) could check for errant behavior.

The Temporal Expression language is generally useful in contexts other than circuit simulation.  This project liberates the old code from the Verilog scheduler, making Oroboro Temporal Expressions useful in for property checking in real-time in complex systems.  These days they are finding a use in Agentic systems as correctness checkers.

## Example

Temporal Expressions in Oroboro are cycle-based, with a cycle denoted by the posting of a periodic event.  For a specific temporal expression, this is called the "sampling event."  Oroboro is designed to be embedded in a driving process that defines the code that is to be monitored.  The driving process should post the sampling event.

The following shows how to write a temporal expression that expresses the constraint of the earlier example.

- whenever there is a REQUEST, an ACKNOWLEDGEMENT must be present 2 cycles later, with no intervening ACKNOWLEDGEMENT.

First, we need to write Python code that detects the presence of a request and the presence of an acknoledgement.  These functions examine the environment of the driving process to determine if the relevant condition is true at the instant of the sampling event.  The functions must only examine current state, and must not block.

``` python
def isRequest():
    # examine state in the Python environment to calculate true or false
    truth = ...
    return truth
       
def isAck():
    # examine state in the Python environment to calculate true or false
    truth = ...
    return truth
```
    
Next, we'll define some supporting code.

``` python

# instantiate the Oroboro executor
oro = Oroboro()

# define a sampling event that the environment will post
psmplr = ObserverEvent()

# print a MATCH
def onmatch(trace):
  print(f"MATCH DETECTED: {trace}")
  
# print a FAILURE
def onfail(trace):
  print(f"FAILURE DETECTED: {trace}")
```

Next, we will define a checker task.  This will be a Python generator that will execute as an Oroboro task.  It first defines the predicates `req` and `ack` in terms of the functions defined earlier.  The `Pred` constructor is very important.  It creates a one-cycle temporal expression from a function.  A predicate *matches* at the current sampling event if its function returns `true` and *fails* if its function returns `false`.

Next, the temporal expression is constructed by combining predicates with the operators `>>`, `~` and `+`.

- `>>` : if the LHS matches on the current cycle, then the RHS must match on the next cycle
- `~`  : turns a match into a failure, and vice versa
- `+`  : the LHS must match on the current cycle and the RHS must match on the next cycle

The resulting temporal expression spans three cycles.

Then an assertion is made with the `always` function: this states that it is always true that on each posting of the sampling event, the expression must be true.

If there is a match of the temporal expression, an execution trace will be sent to the `onmatch` function, which will print it.  Similarly, if there is a failure to match, the failure will be sent to the `onfail` function.

``` python
def checkerTask():

    req = Pred(isRequest)
    ack = Pred(isAck)

    te = req >> ~ack + ack
  
    always(psmplr, te, onmatch=onmatch, onfail=onfail)
  
    yield Timeout(0)
```

Lastly, the checker task can be given to the Oroboro scheduler to start as its main task.  The calling environment can then drive the Oroboro scheduler.

``` python
# register the checker task with Oroboro
oro.start(checkerTask)


# Drive Oroboro from the User's Environment
while true:

  #
  # the environment performs time-advancing operations and alters state
  #

  t = time.time()        # get the current_time

  oro.post_at(t, psmplr) # post the event at the time
  oro.run_until(t)       # run the scheduler up to and including the time

```


## Dependencies and Tests

Oroboro Temporal Expressions have no special dependencies beyond `pytest` for running the tests.

To run all of the tests:

    python -m pytest
    
To run a specific test, or tests matching a prefix:

    python -m pytest -k test_te_cond0
    
To run a test and print the output log:

    python -m pytest -k test_te_cond0 -s
    

## Limitations

The current code is not properly re-entrant.   Only one instance of the Oroboro scheduler may exist at a time.
    

## A Summary of the Operators

- `Pred(fn)` : matches if the function returns `true`, fails if the function returns `false`

- `+` (concatenation) : if a and b are temporal expressions, then (a+b) is a temporal expression that matches where first a matches and then b.

- `/` (fusion) : Fusion is similar to concatenation except that it does not wait for a cycle between its arguments. If a and b are temporal expressions, then (a/b) is a temporal expression that matches where a first matches, and then b in the same cycle of a.

- `|` (alternation) : Alternation matches where either of two expressions match. If a and b are temporal expressions, then (a|b) is a temporal expression that matches where either a matches or b matches.

- `^` (intersection convolution) : Intersection matches if both expressions match, and provides a match for all the ways that the two match.  If a and b are temporal expressions, then (a^b) is a temporal expression that matches where a matches for each match of b before it, and matches where b
matches for each match of a before it.

- `&` (conjunction) : Conjunction matches if both expressions match at the same time. If a and b are temporal expressions, then (a&b) is a temporal expression that matches where a and b both match with the same start and end time.

- `*` (repeat) : The repeat operator implements successive concatenation. If a is a temporal expression, then (a\*n) is a temporal expression that matches where a matches n times in succession. As with concatenation, a sampling event interval is inserted after each match of a.

    The repeat operator supports a more general form a\*(n,m), where n and m are integers greater than 1. In this form, a match if any of [a\*n, a\*(n+1), ... a*(m)] match.  

    Repeat is not defined for values of n or m <= 0.

- `>>` (conditional) : The conditional operator gates the evaluation of its second argument by successful completion of its first
argument. If a and b are temporal expressions, then (a>>b)
    - matches if a fails, at the time of the failure
    - matches for each match of a followed by a match of b
    - fails otherwise
    
- `~` (inv) : The invert operator inverts the match/failures sense of its argument. If a is a temporal expression, then (~a)
is a temporal expression that matches if a fails, and fails if a matches. The time at which the result of (~a)
produces its match or failure is at the time of the last match or failures of a.

### Filters

Filters are a subcategory of temporal expression operator that exist to selectively pass a subset of the
events detected by a more general temporal expression.

- `firstof` : This operator is a filter. Its argument is a temporal expression. For each evaluation of the temporal expession a, firstof(a) matches at the first match of a, and fails if a fails. The firstof operator is most often used to enhance performance so that unneeded evaluations are not performed.

- `once`  : This operator is a filter. Its argument is a temporal expression. For each evaluation of the temporal expression a, once(a) matches only once at each cycle where a matches, or fails if a fails. This operator does not suppress the matches of its argument from occurring, but does not pass them on to its parent. If the execution time of the parent expression is sensitive to the number of matches, then this operator may be used to enhance performance. More often, it is used to simplify expressions that inadvertently match multiple times at the same simulation step.


## Explanation of Multiple Matches

The evaluation of a temporal expression begins at a particular cycle and succeeds with one or more matches, or it fails to match at all.  This section will use a visual representation to explain how this works.

The explanation begins with the simplest temporal expression, a predicate temporal expression.  In the following, the predicate `a` is a temporal expression that matches when `siga==1` and fails otherwise. 

``` python
def fna():
    return sig1 == 1

a = Pred(fna)
```

The visual trace of the evaluation of the temporal expression `a` starting at cycle 2 is a match, shown in the figure below as an 'm'.  The CYCLE number is on the top line, and the value of the state variable `siga` is shown on the next line.
 
The evaluation of the predicated at cycle 2 starts at cycle 2 (shown with an 's') and ends at cycle 2 with a match (shown with an 'm', also at cycle 2).
 
 
    CYCLE    0   1   2   3   4   5   6
    siga     0   0   1   1   0   0   0  
                    ---
                     s
    a                m
	
The evaluation of this Predicate temporal expression at cycle 4 starts and ends with a failure.

    CYCLE    0   1   2   3   4   5   6
    siga     0   0   1   1   0   0   0  
                            ---
                             s
    a                        f
	

Now let's consider how the evaluation of a temporal expression that spans multiple cycles.   The expression

    ex = (a + a)
	
spans two cycles, and matches if there is a match at its starting cycle, and a match on the following cycle.  Evaluation at cycle 2 can be represented as shown below.


    CYCLE    0   1   2   3   4   5   6
    siga     0   0   1   1   0   0   0  
                     -----
    ex               s   m

This expression would begin evaluation at cycle 2, and would produce a match at cycle 3.

Multiple matches are produced from operators that evaluate alternatives (such as 'alternation' and 'repeat').  For instance, the expression

    ex = (a + a) | (a + a + a)
    
evaulated at cycle 2 with the `siga` trace shown below would produce two matches.  One at cycle 3 and another at cycle 4.

    CYCLE    0   1   2   3   4   5   6
    siga     0   0   1   1   1   0   0  
                     ---------
    ex               s   m   m

The matches are emitted to the `onmatch` function as a trace.  The trace data structure indicates the beginning and end of the interval matched, and how it matched.

The `always` assertion launches an evaluation of a temporal expression *at every cycle*.  For example, the assertion

    ex = (a + a) | (a + a + a)
    always(smplr, ex, onmatch=..., onfail=...)
    
evaluated against the given trace can be represented visually as shown in the below figure for the first 5 cycles.  The evaluation at cycle 0 fails immediately, as does the evaluation at cycle 1.  The evaluation beginning at cycle 2 will produce two matches and then stop.  The evaluation beginning at cycle 3 will produce one match, one failure and then stop.  The evaluation at cycle 4 will fail and stop at cycle 5.

    CYCLE    0   1   2   3   4   5   6
    siga     0   0   1   1   1   0   0
             - 
    ex       f

                 -
    ex           f
    
                     ---------
    ex               s   m   m
    
                         -----
    ex                   s   m

                             -----
    ex                       s   f


## Summary

Oroboro Temporal Expressions are a concise notation for expressing sequences over time in an event-driven framework.  The sampling event defines when predicate conditions are evaluated and moves the evaluation of expressions forward.  Matches and failures are delivered to user code as they are detected through the `onmatch` and `onfail` callbacks so that error logging or error correction may be undertaken.  A trace data structure accompanying a match or failure illustrates how the match or failure was detected.
