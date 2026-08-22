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
