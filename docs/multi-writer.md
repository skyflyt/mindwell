# Multi-writer safety

File-sync services are not transactional databases. A local lock cannot protect another computer, and a shared lock can itself arrive late.

For high-value files, combine:

- a local atomic lock;
- a shared expiring lease;
- a last-committed content hash;
- verification immediately before mutation;
- unique log fragments rather than shared appends.

The committed hash is essential: when replica A commits `v2`, replica B must compare its local target with the shared `v2` baseline before writing. If B still has `v1`, it stops before mutation.
