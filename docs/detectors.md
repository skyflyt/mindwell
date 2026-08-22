# Detectors and receipts

A second brain that runs unattended work needs detectors: checks that notice
when a scheduled task died, a backup stopped landing, a note stopped being
written. This document is about the way those detectors fail, because they
fail in one characteristic way, over and over:

**A detector that measures a proxy for the thing, rather than the thing
itself, is indistinguishable from a working detector until the day it
matters.**

Every pattern below was paid for in production. Each is written as: the proxy,
how it burned, and the fix.

## The proxy catalogue

### An exit code is not the work

A task can return zero and have produced nothing — or hang forever on an
interactive prompt and return nothing at all. Verify the *side effect*: the
file it should have written, the log line it should have appended, the process
it should have restarted. A task that stopped misbehaving because it stopped
running is a failure, not a fix.

Corollary: a build step that checks "does the output file exist" will happily
report success over *last week's* output file when today's build failed.
Require a zero exit **and** an artifact timestamped by this run — and make the
failure message name the stale artifact, so nothing downstream picks it up.

### Repository activity is not "the backup ran"

A liveness check aged the most recent commit — by any author — to decide
whether the hourly backup job was alive. Other writers kept the repository
looking fresh while the backup job failed 48 consecutive runs. Nobody noticed
for two days. Commit age answers "did anything commit"; it cannot answer "did
*this job* do *its* work." Only a receipt written by the job itself can.

### File modification times are not freshness

Checkouts, rebases, and sync clients rewrite mtimes wholesale; an
mtime-keyed index will re-embed the entire vault after a sync storm, and an
mtime-keyed staleness check on a version-controlled file may *never* fire,
because routine repository operations keep freshening it. Hash content to
detect change; read the date a record carries *inside itself* to judge its
age. The same applies to run stamps after an outage: when a machine wakes
from a day offline, every scheduled task fires in one catch-up burst and the
stamp times cluster — they record the burst, not when the work was due.

### A freshness check keyed to a format is keyed to the format

A staleness check aged the newest dated *heading* in a log file. The write
path later changed to append dated *bullets* instead — and a file appended to
three times that day read as four days stale, tripping a false alarm that
masked nothing but cost an investigation. When the write path changes, every
detector keyed on the old shape silently changes meaning. Age the newest
entry in *any* shape the file can legitimately contain, and take the maximum,
so a date merely quoted inside an entry cannot drag freshness backwards.

### A naming convention is not an inventory

Two health checks matched scheduled tasks by a name prefix. More than a third
of the registered tasks — including the only off-machine backup — matched no
prefix and therefore had no surfacing at all. Drive coverage from a declared
registry instead, and make **both** directions a finding: a live task with no
registry entry, and a registry entry with no live task. For a dead-man's
switch, the second direction is the one that matters — from inside the
scheduler, an absent watchdog looks identical to a healthy one.

Keep the *reason* a thing is exempt next to the thing, in the registry, not
in an array inside the checker — and cross-check the exemption names, so a
typo'd exemption surfaces instead of silently matching nothing.

### A tool's own "verify" checks what the tool cares about

`git bundle verify` passes on a bundle with two megabytes of garbage appended
— it reads the header, not the pack. A backup check that stops at the tool's
own verification is asserting less than it appears to. Verify the artifact:
present at every destination, fresh, structurally valid, checksum-matched
against a sidecar written at creation, and containing a tip that exists in
the source repository.

And even all of that proves the backup *landed*, not that it *restores*. Only
a restore drill proves a restore — and a drill that exists but has no
schedule and no receipt is a comment, not a control. Where a check can only
see a proxy, make it say so in its own output rather than imply more.

### A check that needs an account under-reports what has no account

A monitor that can only check devices it can log into silently redefines
"the estate" as "the credential inventory" — the uncovered machines are
invisible rather than flagged. Define coverage by something that needs no
credential (a reachability probe: even a connection *refusal* proves the host
is alive), and make the uncovered set visible rather than absent.

### Ask what the method is structurally capable of seeing

A license report counted directory-group members to report purchased seats.
The number happened to match the vendor console, so it looked correct — it
was correct *by luck*. An unassigned seat has no user attached to enumerate;
the method is structurally incapable of ever showing one, whether the gap is
one seat or fifty. Before trusting a number that agrees with reality, ask
whether your counting method could have disagreed.

## Receipts: the fix that generalizes

The repeated answer above is a **receipt**: a small record the job writes
about its own completed run — verdict, timestamp, and *whether the result was
delivered* — placed where an independent check can judge it.

- **"Found problems" and "told the human" are different facts.** Only the
  second ends an outage. A monitor once computed correct findings every
  fifteen minutes for nine days while its delivery credential was expired:
  two hundred alerts, delivered to nobody. The receipt must record delivery,
  not just verdict.
- **Track receipts in version control.** A gitignored status file is invisible
  to every other machine and dies with a reinstall.
- **Write the heartbeat at the end of the work, never the start.** A ping at
  the top of a script proves the process started; a ping on the completion
  path proves the run finished. Skip it on fatal exits and delivery failures
  — for a dead-man's switch, silence *is* the alarm, so a heartbeat sent on a
  failed run defeats the switch.

## A check that measures itself is not a check

The health check's own run failed, and nothing noticed — because the check
was the thing that would have noticed, and one scheduler quirk makes the
trap explicit: while a task is running, the scheduler reports "currently
running" *as that task's own last result*, so a task reading its own status
reads its own liveness and calls it success.

The shape that works: the check writes a run receipt; a **separate watchdog
process, on a separate trigger, with its own delivery path**, judges that
receipt — so a broken alerting path cannot swallow the news that it is
broken. The main check watches the watchdog in return. Two processes watching
each other is not the same as either watching itself.

And prove the alarm in a **copy** of the world: induce failure states in
doctored fixtures, not by disabling the real safeguard — a test that switches
off the real backup task to see whether the alarm fires *becomes* the outage
if it dies halfway.

## Alerting state must outlive the run that ends the problem

An alert flag that lives in an ignored file and is cleared by the next
successful run **erases the outage by the act of ending it** — nine days of
failure vanished from the record the moment the failing job succeeded once.
Durable alerting state is: tracked in version control, keyed on the finding,
and **resolved rather than deleted**, so history survives.

Key each finding individually. An all-or-nothing flag per writer means one
standing finding freezes retraction of everything else that writer owns — and
the real hazard is not the noise: a *genuine* problem arriving behind a stale
finding inherits an already-raised flag and never reads as new. Raise and
retract one key at a time, unconditionally, on every pass.

Two more rules keep a register alive:

- **A detector that records into a file nobody opens is indistinguishable
  from no detector.** Wire findings into a channel that already reaches the
  human.
- **Match the alert cadence to the decision cadence.** A weekly decision
  needs a weekly alert. Detectors that alert daily on findings nobody can act
  on daily get muted, and a muted detector rots. Retiring a noisy check on
  measured evidence (flags raised vs. true positives) is maintenance, not
  defeat.

## An alert asserts only what it can observe

An alert once said "X is NOT being checked" when the truth was "this machine
cannot currently *see* the checker" — the checker was fine, and the alert
sent the responder to the wrong component. State what you know from where you
stand ("state UNKNOWN from here"), and name where to start looking. An alert
that misroutes the responder is worse than a vague one.

## The four legs of a non-vacuous green

A scanner ran on schedule for sixteen days writing a receipt nobody read —
its check had been renumbered out from under it. When re-wiring it, "the scan
ran" turned out to be only a quarter of what a green light should mean:

1. **It ran** — the receipt exists and parses *as a receipt* (a corrupted
   receipt can still be valid JSON).
2. **Its engine still detects** — a self-test plants known findings and
   confirms the scanner sees them, so green cannot come from a scanner that
   quietly stopped matching.
3. **The read was representative** — report how much of the surface was
   unreadable; "clean over 80% of the files" is not clean.
4. **Somebody looked** — new findings drive the state, so a run that found
   fifty things nobody triaged is not a pass.

One housekeeping rule from the same incident: if you renumber or rename a
check, grep for the old name first. A document promising "check N judges
this" outlives check N.
