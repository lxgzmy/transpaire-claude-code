---
name: humanizer
description: >
  Strip AI-writing tells from any draft before a person reads it. Use on every
  human- or client-facing text: emails, summaries, documents, alerts, reports.
  Removes em/en dashes, rule-of-three padding, AI buzzwords, sycophancy, filler,
  signposting, and formulaic structures, then calibrates to a real writing
  sample when one is provided. Generic de-AI engine; the transpire-writing
  skill layers the Transpire house voice on top of this.
---

# Humanizer (de-AI patterns)

Make text read as if a busy, competent person wrote it. Work through the
numbered patterns, fix every hit, then do the final read-through.

Organisation-neutral on purpose: it carries no Transpire voice. For anything
written **for Transpire**, invoke `transpire-writing` instead, which runs these
patterns as its first step and then applies the house voice.

## Patterns to remove

1. **Em and en dashes.** No `—` or `–` anywhere. Rewrite with a comma, a full
   stop, parentheses, or a restructured sentence.
2. **Rule-of-three padding.** "fast, simple, and reliable" style triplets used
   for rhythm rather than content. Keep the one or two items that matter.
3. **AI buzzwords.** delve, vibrant, tapestry, testament, landscape, robust,
   seamless, leverage, unlock, elevate, foster, empower, journey, navigate,
   crucial, pivotal, comprehensive, "in today's fast-paced world". Replace
   with the plain word or delete.
4. **Sycophancy.** "Great question!", "You're absolutely right", "Happy to
   help!". Delete; answer directly.
5. **Filler and signposting.** "It's important to note that", "Let's dive in",
   "In conclusion", "As mentioned above", "I hope this helps". Say the thing
   without announcing it.
6. **Hedging stacks.** "may potentially", "could possibly", "it seems that it
   might". One qualifier at most, and only if the uncertainty is real.
7. **Formulaic contrasts.** "not only X but also Y", "It's not X, it's Y",
   "whether you're A or B". Rewrite as a direct statement.
8. **Over-structuring.** Bullet lists and headings where two sentences of
   prose would do; bold-term-colon lists ("**Speed:** it is fast"). Prefer
   prose for anything under four items.
9. **Uniform rhythm.** Every sentence the same length and shape. Vary short
   and long; let one sentence carry one idea.
10. **Empty wrap-ups.** Closing paragraphs that restate what was just said.
    End when the content ends.
11. **Exclamation marks and emoji** in professional text. Remove.
12. **Title Case Headings.** Use sentence case.

## Voice calibration (outranks everything above)

If a real writing sample from the intended author or organisation is provided,
match it: register, sentence length, vocabulary, sign-off. The sample wins
wherever it conflicts with the default patterns. Never copy the sample's
facts, only its voice.

## Method

1. Scan the draft against patterns 1–12 and fix every instance.
2. Calibrate to the sample if one was given.
3. Read the result once more as the recipient. If a sentence sounds like a
   press release or a chatbot, rewrite it plainly.
4. Never add, drop, or alter facts, names, numbers, dates, or amounts while
   rewriting. Flag missing detail; do not invent it.

## Embedded mode

When used as a step inside another skill or task, output only the corrected
text. No commentary, no list of changes, no ceremony.
