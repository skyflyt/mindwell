# Grounded claims

A second brain is a record. The systems it describes — ticket queues,
calendars, budgets, code — are the reality. This document is about the ways a
well-maintained record quietly diverges from reality, and the conventions
that keep an agent from presenting one as the other.

Everything here comes from real incidents, anonymized.

## Superlatives are artifacts of when the record began

An agent's notes asserted that one person was *the only one who had ever*
closed a particular class of work item. The live system of record showed
hundreds of closures by a dozen people; the named person accounted for about
four percent. The notes were not wrong about what they contained — they
simply began recording three days before the claim was made, and nothing
before that existed in them.

A superlative derived from an append-only record that began mid-history is
not a finding; it is an artifact of the start date. Before writing *only*,
*first*, *never*, or *nobody has ever*, ask what the source could have seen.
If the source is your own notes, the honest sentence is **"the record
contains no instance of"** — a much weaker and much safer claim.

## How a qualified claim becomes an unqualified one

The false claim above reached seven files through four hops, each locally
reasonable:

1. A scheduled run wrote, accurately: "the only closure this project has ever
   **recorded**." (It had queried the live system for the *open* queue but
   read its own notes for *closures* — see the next section.)
2. A weekly summary repeated it, still qualified.
3. A hand-written note forty minutes later reached for the line as context
   and **dropped the qualifier** — a statement about what the record
   contained became a statement about what had happened.
4. The nightly memory update promoted the unqualified version into the
   standing-facts file — the file quoted back into every future session.

No step was careless. The failure is that nothing between step 1 and step 4
could tell "we have no record of X" apart from "X never happened", because
the only source consulted was the record. Guard the *rewrite* hops: any
paraphrase of a scoped claim must keep the scope, and promotion into standing
memory is the point of no return — that is where one day's note becomes a
fact every future session inherits.

## A mixed-source answer is confidently wrong

The run in hop 1 queried the live system for one half of its question and its
own notes for the other half, then composed the halves into one answer. The
live half was right; the notes half was incomplete; the composite read as
uniformly authoritative. When auditing a claim, ask *which half came from
where*. Counts, totals, and "current state" belong to the system of record —
"closures" must come from a closed-status query, never from note history.

## Corrections propagate; receipts do not

When a claim is found false, correcting the file you noticed it in is not the
fix — the claim has already traveled. The convention that worked:

- Find **every** location the claim reached and correct each **in place**,
  with the original wording struck through and readable, each correction
  pointing at one canonical write-up of what actually happened.
- **Never rewrite receipts or audit trails** — consumed journal entries and
  processing scratch files record what was written at the time; rewriting
  them falsifies the trail that makes the correction checkable.
- **Keep retracted false alarms visible, with their reasoning.** One
  retraction note kept the wrong arithmetic struck-through precisely
  "because the arithmetic is inviting and the next reader would redo it." A
  deleted false alarm gets re-derived; a struck one is a warning sign at the
  exact spot of the trap.

## A snapshot that cannot say what it is will be read as what it looks like

A point-in-time snapshot — written to make a restructure reversible — sat in
a prominent location for a week. A later session read one figure out of it
and concluded that a request approved *after* the snapshot "does not exist."
Nothing was wrong with the file; it was seven days old and looked like a
statement of current position. It even outranked the conventions document
that described the correct current shape, purely by sitting somewhere more
visible.

The fix is a banner convention. Every snapshot opens with a blocking
**NOT CURRENT** banner that names:

1. the capture date;
2. the live source, with the exact query to run against it;
3. what is specifically known to have changed since capture;
4. the instruction to assume everything else is stale too.

With frontmatter to match (`type: snapshot`, `status: point-in-time`, what it
is a snapshot *of*, and where the live source lives), so tooling can rank it
below current-state pages. And one sentence worth engraving in any
conventions document: **the live system is the record; nothing in the vault
is.**

## Write rules for the misreader

A conventions rule read "One X per Y. Always." It was written to stop one
error (bundling several Y's into one X) and was read as its converse — a cap
of one X per Y — and used to merge two unrelated things, destroying structure
for nothing. A rule is not written for the person who already understands it.
When a rule gets misapplied:

- Reword it as the constraint it actually is — a **ceiling, not a floor**
  ("no X spans more than one Y", not "one X per Y").
- Record the misreading **inline, dated**, so the next reader sees the
  failure mode at the spot where it happened.
- Give it a one-question acceptance test ("does this contain items belonging
  to more than one Y? If yes, split. If no, it is already correct, whatever
  else Y has").
- Say explicitly what is **not** a finding ("a Y holding several X's is the
  normal shape") — checklists that only name violations teach reviewers to
  see violations everywhere.

## A summary is an unverified claim about a source you still hold

A meeting digest asserted the opposite of what its transcript said about a
person's availability — the summarizer dropped a negation. It was caught only
because someone cross-checked the raw transcript. A digest that silently
inverts a fact is worse than no digest, because everything downstream reads
it as sourced: the inversion inherits the credibility of the transcript it
cites.

When you hold the source, verify the summary against it: anchor each claim to
the passage that supports it, and run a deterministic guard for dropped
negations — the one error class that flips meaning while preserving every
keyword a fuzzy match would look for.

A sibling trap from the same system: two ingest pipelines both filtered on
the same field, so an item that failed the filter was invisible to both — and
the gap read as "nothing to ingest" rather than as a miss. Two lanes sharing
a filter are one lane. Add a cross-source coverage check so a future miss
*surfaces* instead of passing silently.
