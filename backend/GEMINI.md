# Gemini annotation layer

## What it does

Adds pharmacological context to the ranking. For each drug: its molecular
target and mechanism class. For each top-ranked pair: why the combination is
or is not mechanistically plausible.

## What it does not do

It does not touch the prediction. No score, interval, tier or ranking in this
project is produced or modified by an LLM. The ranking is a random forest over
measured NCI-ALMANAC data, validated on held-out pairs; if a language model
influenced it, none of those validation numbers would mean anything.

Every annotation in the API response carries `"is_measurement": false` and
names the model that produced it. That field is there so the distinction
survives contact with whoever consumes the API next.

## Self-consistency

Each question is asked five times at varying temperature. The answer kept is
the majority vote on a categorical field (`mechanism_class` for drugs,
`rationale_type` for pairs), and the `agreement` fraction is recorded.

Voting runs on the enum rather than the prose because two differently-worded
sentences are not a disagreement. The free text returned comes from a sample
that voted with the majority.

An annotation at 5/5 agreement and one at 2/5 are different objects, and the
output says which it is. Anything below 0.6 is flagged `low_confidence`.
`--stage summary` reports how many came out shaky — read it before quoting
any of this.

The prompts tell the model to answer "unknown" or "no clear mechanistic
rationale" when there isn't one. Those are correct answers, not failures. A
high rate of them is information about the shortlist, not a bug.

## Running it

```bash
pip install google-genai
export GEMINI_API_KEY=...            # aistudio.google.com/apikey

python annotate.py --dry-run         # no API calls - check the plumbing
python annotate.py --stage drugs     # ~105 drugs x 5 samples
python annotate.py --stage pairs --limit 200
python annotate.py --stage summary   # agreement stats
```

Results append to `annotations/*.jsonl` as they complete, so a crash or a
Ctrl-C costs nothing — re-running skips what is already done.

Run `drugs` before `pairs`: the pair prompts use the drug targets, and the
rationale is better for it.

Environment variables: `GEMINI_MODEL` (default `gemini-flash-latest`),
`GEMINI_SAMPLES` (5), `GEMINI_WORKERS` (8),
`ANNOTATION_MIN_AGREEMENT` (0.6).

## Wiring

`annotations.py` loads the CSVs at startup and attaches them to `/pair` and
`/shortlist`. It is inert when the files are absent — the API runs with no
Gemini dependency at all, `annotations_loaded` reports `false`, and the
`annotation` field comes back `null`. Verified both ways.

## Cost

Flash, short prompts, ~5,000 calls for drugs plus 200 pairs at five samples
each. Small. Use Flash for bulk; Pro only if you add the literature stage,
where volume is low and the reasoning is harder.

Don't use the Batch API for this. Tier 3 raises batch queues to a billion
enqueued tokens, but batch jobs are asynchronous with unpredictable
turnaround. Interactive calls at Tier 3 are fast enough.
