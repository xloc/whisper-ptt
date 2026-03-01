# Ctrl+C Terminal Input Leak — Investigation & Fix

## The Bug

When pressing Ctrl+C to exit `whisper-ptt`, all previously transcribed and pasted
text would reappear at the shell prompt, as if typed by the user.

## Investigation

We isolated the issue using small standalone test scripts rather than modifying the
main program.

### What we ruled out

| Test | Hypothesis | Result |
|------|-----------|--------|
| Paste only (no pynput) | Paste mechanism itself causes leak | No leak |
| Paste while Listener **active** | Active tap causes leak | No leak |
| `NSApplication.sharedApplication()` alone | NSApp init causes leak | No leak |
| Sleep 0/3/10s after Listener stops | Race condition / async cleanup | Still leaks |
| `stty -a` before vs after Listener | pynput changes tty settings | Settings unchanged |

### What causes the leak

**Paste after a Listener has started and stopped → leak.**

```
with Listener(...) as l:
    pass              # listener stops here
# ← any paste here leaks
```

This state is **permanent** for the process lifetime — no amount of waiting
or starting a fresh Listener restores it. (A second Listener start/stop
actually doubled the leak: `FIX_TESTFIX_TEST`.)

### What the leak looks like

```
pasted LEAK_C — Ctrl+C now
LEAK_C^Cexited cleanly
$ LEAK_C        ← leaked into shell prompt
```

The text appears **twice**: echoed inline during execution (normal), then again
at the shell prompt after exit. This means Ctrl+C delivered SIGINT to Python
(the signal handler fired, the script exited cleanly) but **did not flush the
pty input buffer** — the pasted text remained and the shell processed it on
resuming.

### Root cause (partially understood)

pynput's `Listener` creates a `CGEventTap` (macOS system-level keyboard hook).
After the tap is stopped, something about the event routing is permanently
altered so that Ctrl+C no longer triggers the pty driver's input buffer flush,
even though tty settings (`ISIG`, `NOFLSH`) are visibly unchanged. Neither
`NSApplication` initialization nor timing explain it — it is specifically the
CGEventTap lifecycle. The exact mechanism was not fully identified; a bare
Quartz `CGEventTap` test (`test_cgeventtap.py`) was written but not run before
the fix was applied.

## The Fix

The key observation: **paste while the Listener is still active = no leak** (mode B).

The original code created a new `Listener` on every call to `record()`, stopping
it when the hotkey was released — before transcription and paste. This meant every
paste happened in the post-stop state.

**Fix**: hoist the `Listener` into `main()` so it lives for the entire program
lifetime. It starts once, wraps the whole recording loop, and only stops when the
program exits. All pastes happen while it is still active.

```python
# Before: listener created and destroyed on every recording cycle
def record(hotkey):
    with Listener(...) as listener:   # stops before paste
        ...
    return audio

while not stop.is_set():
    audio = record(hotkey)
    ...
    kbd.tap('v')   # paste — AFTER listener stopped → leak

# After: one persistent listener for the whole session
with Listener(on_press=on_press, on_release=on_release) as listener:
    while not stop.is_set():
        audio = record(pressed, released, listener)
        ...
        kbd.tap('v')   # paste — listener still active → no leak
```

`record()` no longer manages its own `Listener`; it receives the shared `pressed`
and `released` events (and `listener` for the liveness check) from `main()`.
