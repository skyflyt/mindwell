# Multi-writer safety

File-sync services are not transactional databases. A local lock cannot protect another computer, and a shared lock can itself arrive late.

For high-value files, combine:

- a local atomic lock;
- a shared expiring lease;
- a last-committed content hash;
- verification immediately before mutation;
- unique log fragments rather than shared appends.

The committed hash is essential: when replica A commits `v2`, replica B must compare its local target with the shared `v2` baseline before writing. If B still has `v1`, it stops before mutation.

## Write so failure cannot destroy

A write that truncates before it writes turns every failure into data loss. `Path.write_text` and `open(path, "w")` both do this: the target is empty from the moment the file opens, and an encoding error, a full disk, or a killed process leaves it that way. The caller sees an exception that reads as "the write failed"; what happened is "the file was destroyed." A production vault lost the same file twice in five days to a stray surrogate that raised during the encode, after the truncate.

Mindwell's own writers use `mindwell.fsio.atomic_write_text`: encode first, write to a sibling temporary file, `os.replace` over the target. Vault automations you write yourself should follow the same shape. A reader sees the old content or the new content, never an empty file.

## Verify effects, not actors

Four rules, each paid for:

- **Re-read the thing you changed.** A returned success code says the call completed, not that the content landed where readers will look. After a write that matters, read the target back and compare.
- **Modification time is not freshness in a git-synced vault.** A checkout, a rebase, or an aborted merge rewrites mtimes wholesale. If a check needs to know whether content is current, it must look at the content - a date inside the file, a hash against a baseline - never at the filesystem timestamp.
- **A liveness check must measure the thing itself, not a proxy.** A backup monitor that ages "the most recent commit by any author" stays green while the backup writer is dead, because other writers keep the repo looking fresh. That exact gap hid a two-day backup outage. Ask "did *this* process produce *its* artifact", and alarm on that.
- **An alert is an effect too - verify the delivery, and keep failure records durable.** A deploy monitor computed correct findings every cycle for nine days while its delivery leg failed authentication more than two hundred times: the verdict was part of the run receipt and the delivery was not, so every receipt read green while the findings reached nobody. The only records of the outage were an unversioned log and a status flag that the next successful run cleared - nine days of failure erased by the run that ended them. Record verdict *and* delivery in the receipt, and keep findings in durable, version-tracked state, keyed individually and marked resolved rather than deleted. `docs/detectors.md` develops this into the full receipt-and-watchdog pattern.

## Claim the work before you do it

Path-scoped commits, read-back after write, and verify-before-assert all bound
the damage of a collision that already happened. None of them lets an agent
ask "is someone already on this?" In a production estate two sessions picked
up the same work item at once. One built the fix, merged it, and opened a
change record while the other was still analysing. Inside one minute both
wrote to the same record, and each reported actions it had not performed until
it checked. One session's public reply overwrote the other's. The second
session adopted the existing change record instead of opening a duplicate, and
that good outcome came from judgement, not design.

The claim that closed this gap:

- **Exclusive and machine-local.** Create the claim file with an
  exclusive-create flag (`O_CREAT|O_EXCL`) in a directory outside the synced
  repository, beside the sync lock. A claim committed to the repository reaches
  the other machine minutes after it stopped being true, and it reads as
  authoritative when it arrives.
- **Scoped to one machine, and documented that way.** Across machines, read the
  work board's status as advice only. "In progress" on a board describes the
  item, not whether a session is alive; one item sat "in progress" for nine
  days with nobody on it. A real cross-machine lock needs an atomic claimed-by
  field on the board itself.
- **A TTL derived as a bound.** Set expiry from the longest gap between two
  points where a holder can renew. In that estate the worst back-to-back pair
  of blocking steps ran 25 minutes, so the TTL is 45. Long work renews at each
  checkpoint.
- **Liveness vetoes expiry and never triggers it.** A holder whose process
  still runs, started at or after its claim, in the same boot, does not expire
  however old the clock says it is. "Could not check" is its own answer and
  does not read as "dead". On Windows a successful process-handle open does not
  prove life, because an exited process keeps its kernel object while anyone
  holds a handle; wait on the handle with a zero timeout.
- **Visible expiry.** Move an expired claim aside with an annotation instead of
  deleting it, and tell the displacing session whom it displaced so its report
  says so.
- **A refused claim writes a receipt.** A blocked run that writes nothing looks
  identical to a run that never started.
- **A failed release is a finding.** If release or renew reports the claim was
  already gone, another session may have worked the same item. Re-verify what
  you wrote.

Before opening a record for a deploy, ask whether one already exists for that
commit, and fail closed. A duplicate check that fails open lets the duplicate
through on the day the network is flaky.
