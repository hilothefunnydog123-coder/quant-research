# Contributing to Neil Quant Labs

This is an **open quant research collective**. Anyone may submit a research note
— a reproducible experiment answering a specific question in quantitative
finance. Submissions are peer-reviewed against our methodology standard before
they're merged, so everything published here meets a real bar.

## What we publish

A **research note**: one clear question, a reproducible experiment that answers
it, and an honest write-up — **including null results.** "This doesn't work,
here's the evidence" is a valid and welcome finding. We do **not** publish
get-rich claims, un-reproducible results, or anything that can't be run from
source.

## How to submit (the pull-request flow)

1. **Fork** this repository (top-right "Fork" button on GitHub — makes your own copy).
2. **Copy the [`_template/`](_template/) folder** and rename it to the next
   number + a short slug, e.g. `005-does-friday-beat-monday`.
3. **Write your note** inside it:
   - `experiment.py` — a single seeded, reproducible script that emits your results and figures.
   - `paper/paper.md` — your write-up (use the template's section structure).
   - `README.md` — a short abstract + how to reproduce.
4. **Add your name** to your note's author line and citation.
5. **Open a pull request** back to this repo. A maintainer reviews it against
   the checklist below; once it passes, it's merged and published with **you**
   as the author.

## The bar every note must clear

Straight from [`METHODOLOGY.md`](METHODOLOGY.md) — reviewers check all of these:

- [ ] **Hypothesis stated up front** (no fishing for a result).
- [ ] **No lookahead** — decisions use only past data.
- [ ] **Out-of-sample or multiple-testing control** where relevant.
- [ ] **Realistic costs** charged where relevant.
- [ ] **Reproducible** — one seeded script regenerates every number and figure.
- [ ] **Honest limitations** stated; no overclaiming.
- [ ] **Null results welcome** and clearly reported.

## Credit & licensing

You keep authorship of your note (name on the paper + citation). By submitting,
you agree your **code** is shared under MIT and your **writing/figures** under
CC BY 4.0 — the same dual license as the rest of the repo. Your name always
stays attached.

## Discussion

Have a question or a research idea but not a full note yet? Open a **[Discussion](https://github.com/hilothefunnydog123-coder/quant-research/discussions)**
or an **Issue**. Proposing good questions is a real contribution too.

## Be kind

Reviews critique the *work*, never the person. New researchers are welcome —
everyone's first note is a first note.
