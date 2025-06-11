# oroboro package init

# defines the event loop and handles
from .loop import Handle, ObserverHandle, BaseLoop

# defines the task abstraction using generators as coroutines, and the top-level scheduler, Oroboro
from .oroboro import Event, ObserverEvent, Task, Reason, NoReason, Timeout, WaitEvent, Status, Oroboro

# temporal expressions are built from tasks
from .te import Pred, Firstof, Once, always, never, teevent, teeval

# trace accessor functions
from .te import tetrace_print
from .te import tetrace_dict, tetrace_count, tetrace_scycle, tetrace_ecycle, tetrace_stime, tetrace_etime, tetrace_children
