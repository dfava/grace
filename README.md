# Grace

Grace is a prototype race detector for Golang based on what we call *happens-before sets* (HB-sets).

Go ships with a [race detector](https://blog.golang.org/race-detector) built from the ThreadSanitizer library, [TSan](https://github.com/google/sanitizers) which employs the concept of vector-clocks (VCs).   We built Grace to study the trade-offs between VC-based race detection and HB-set based.

Grace treats channels as first class, meaning, it observes send and receive operations on channels, as opposed to acquire/release operations on the locks protecting channel buffer entries.

For details, check out our [paper on arXiv](https://arxiv.org/abs/1910.12643).


### Data races

Data races can happen when threads cooperate around a pool of shared memory.
Two concurrent memory accesses constitute a data race if the accesses reference the same memory location and at least one of the accesses is a write.  Here is an example from the [Go memory model](https://golang.org/ref/mem):

```
var a string

func main() {
	go func() { a = "hello" }()
	print(a)
}
```

The main function invokes an anonymous function; this anonymous function sets the global variable `a` to `hello`.  Note, however, that the call is prepended with the keyword `go`, which makes the callee run in a separate goroutine (or thread); meaning, `main` continues without waiting for the anonymous function to return.

Both `main` and the anonymous functions access the same shared variable in a conflicting manner: one of the accesses is a write.  Since both the main and the anonymous functions run in parallel and no synchronization is used, the two accesses are also concurrent. This allows us to conclude that this program has a race.

Because data races can lead to counter intuitive behavior, it is important to detect them.


### Data-race detection based on vector clocks

Vector clocks are an efficient way of tracking the relative order of execution of threads (or goroutines).  VCs are based on a notion of local time: each thread keeps track of its own clock; a thread's clock can advance independent from other threads.

Clocks are tracked in vectors.  A vector clock `V` as a function `V : Tid -> Nat`, meaning that `V(t)` is the value of the clock associated with a thread-id `t` according to the vector-clock `V`.


Vector clocks can be used for race detection as follows:

Each thread `t` is given a vector clock, `C_t` where it keeps track of two things:
1. `C_t(t)` records the current time at  `t`, and
2. for another thread `u`, `C_t(u)` records the time of the most recent operation performed by `u` that is known to `t`.  In other words, `u`'s clock can advance without `t` knowing of it. The entry `C_t(u)` is the time of the most recent operation performed by `u` that `t` is aware of.

Recall that, intuitively, a race is when a thread attempts to access a variable without the thread being "aware" of some previous access to that variable. So, when a thread `t` *attempts to write* to variable `z`, the thread must be aware of the previously occurring reads and writes to `z`. When a thread `t` *attempts to read* from `z`, the thread must be aware of the previous writes to `z` (since the are no read-read conflicts, there is no need for `t` to know of prior reads to `z`).

A race detector, then, keeps track of the accesses to each variable. Take one of the early VC-based race detection algorithms, known as [Djit](https://dl.acm.org/doi/10.1145/781498.781529), as example.  There, each variable `z` is associated with two vector clocks: one for read accesses, `R_z`, and another for writes, `W_z`.
When `t` attempts to write to `z`, a race is flagged when either:
- there exist some write to `z` not known to `t`, meaning `C_t ⊑ W_z`, or
- there exist some read from `z` not known to `t`, meaning `C_t ⊑ R_z`.

When `t` attempts to read from `z`, a race is flagged when there exists a prior write not known to the thread, meaning `C_t ⊑ W_z`.  (As discussed previously, there is no need to check `R_z` when a read is attempted since there are no read-read conflicts).

When a thread succeeds in accessing memory, the vector clock of the memory location is updated to reflect the time of the access.  Precisely, when a thread `t` writes to `z`, the clock `W_z(t)` is updated to `C_t(t)`.  If, instead, the access is a read, then `R_z(t)` is updated to `C_t(t)`.

Although we won't explore this in detail here, it's worth pointing out that the detector described in the previous paragraph can be improved.  As opposed to remembering writes to `z` in a vector clock `W_z`, a detector can remember only the clock and the thread identifier associated with the most recent write to `z`.  Similarly, the detector does not need to track all reads from `z` but only the reads that have accumulated after the most recent write.  This improvement over Djit lead to an algorithm known as [FastTrack](https://dl.acm.org/doi/abs/10.1145/1542476.1542490).

The last piece of the puzzle is how a thread's vector clock is updated.  Threads "learn" about each other's progress when they synchronize.  In the case of Go, synchronization is done via message passing.  In the case of locks, synchronization is done via `acquire` and `release` operations.

Each lock `m` is associated with a vector clock `L_m`. When a thread `t` acquires `m`, the thread learns about about memory accesses performed by the thread who last released the lock.  More precisely, the vector clock of the thread, `C_t`, is updated to `C_t ⊔ L_m`.  When a thread `t` releases a lock `m`, the vector clock of the lock, `L_m`, is updated to `C_t` and thread's clock is advanced, meaning `C_t(t) := C_t(t)+1`.


### Data-race detection based on happens-before sets

In the happens-before set approach, a memory location keeps track of the most recent write onto that location, and of the most recent reads that accumulated after the write.  Technically, not all reads need to be recorded, only the most recent reads that are not ordered.  For example, if thread `t` reads from `z` and then reads again, the second read subsumes the first.  Similarly, a thread keeps track of the reads and writes to memory that it is "aware of".

The difference with vector-clocks is that we track individual accesses, which means that we consume more memory.  Vector-clock based race detectors have a worst-case memory consumption of `O(τ)` per thread, where `τ` is the number of entries in the vector, which is capped by the number of threads spawn during execution.  The per-thread memory consumption of happens-before sets is `O(ντ)` where `ν` is the number of shared variables in a program.

Vector clocks' memory efficiency, when compared to happens-before sets, come from VC's ability to succinctly capture the per-thread accesses that take place in between advances of a clock. A thread's clock is advanced when the thread releases a lock. All accesses made by a thread `t` in a given clock `c` are captured by the clock: if another thread `u` "knows" the value `c` of `t`'s clock, then `u` is in *happens-after* with all accesses made by `t`---that is, all accesses up to when `t`'s clock was advanced to `c + 1`. In contrast, the happens-before set representation is much more coarse. We keep track of individual accesses, as opposed to lumping them together into a clock number. This coarseness explains the extra factor of `ν` in the worst-case analysis of the happens-before set solution. Although being a disadvantage in the worst case scenario, happens-before sets do provide some benefits.

The vector clocks associated with threads and locks grow monotonically. By growing monotonically we do not mean that time marches forward to increasing clock values. Instead, we mean that the number of clocks in a vector grows without provisions for the removal of entries. This growth can lead to the accumulation of "stale" information, where by stale we mean information that is not useful from the point of view of race detection. This growth stands in contrast to HB-set's approach to garbage collection. Stale information is purged from happens-before sets, which means they can shrink back to size zero after having grown in size.


We conjecture that an approach that purges stale information from VCs, similar to HB-set's notion of garbage collection, would be highly be beneficial.


### Grace's implementation

We wrote a prototype of Grace, a happens-before-set based race detector for Go. The race detector observes and tracks relevant events from the execution of a Go program.  The events are:

- `go`, goroutine initialization,
- `read` and `write` events to a variable, and
- operations on channels, `send`, `recv`, `close`

The prototype is written in Python, in `grace.py`.

The prototype can be fed traces "manually" by calling functions in the `Grace` class.  The prototype can also consume traces from TSan, using a layer `t2g.py` that translates calls to TSan into Grace events.  To that end, TSan needs to be recompiled as to print certain calls from the Go runtime; see `tsan_patch.diff`.


### Citing

```
@InProceedings{fava.steffen:sbmf19,
  author    = "Daniel Fava and Martin Steffen",
  title     = "Ready, set, {G}o! {D}ata-race detection and the {G}o language",
  booktitle = "To appear in the pre-proceedings of the Brazilian Symposium on Formal Methods (SBMF)",
  year      = 2019,
  note      = "\url{http://arxiv.org/abs/1910.12643} ",
}
```
