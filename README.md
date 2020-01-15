# Grace

A prototype race detector for Golang.


Go ships with a [race detector](https://blog.golang.org/race-detector) based on the ThreadSanitizer library, [TSan](https://github.com/google/sanitizers).  Why write a new race detector?

Grace is based on an approach we calls *happens-before sets* (HB-sets), while TSan is based on vector-clocks (VCs).  We built this prototype to study the trade-offs between VC-based race detection and HB-set based.

Also, Grace treats channels as first class, meaning, it observes send and receive operations on channels, as opposed to acquire/release operations on the locks protecting channel buffer entries.
