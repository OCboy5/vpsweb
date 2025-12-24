Love the project and the direction you’re taking. Your T–E–T pipeline is already strong: you’re getting faithful, musical drafts, and the “editor” is giving concrete, line-level fixes. To push toward the absolute ceiling of LLM capability (and start rivaling top human translators), I’d focus on four things: better candidate generation, stricter faithfulness guardrails, deeper musicality control, and stronger comparative evaluation. Below is a practical proposal with prompt upgrades, workflow tweaks, and a tiny bit of ops advice.

High‑impact workflow upgrades
- Add a Candidate Generation stage before the current “Initial Translation”
  - Generate 3–5 full translations, each in a distinct strategy lane: literal-leaning, balanced modern-poetic, foreignizing (retains cultural texture), domesticated with meter/rhyme, and “bold equivalence” (permission to re-form for musicality with flagged deviations).
  - Keep outputs compact but self-contained, so later agents can “quote and splice.”
- Add a Judge/Aggregator between Editor and Revising Translator
  - A separate “referee” ranks the candidates plus the edited draft against a clean rubric (faithfulness, naturalness, musicality, cultural resonance), then proposes a composite “best-of” version with line-level picks.
  - This is where you push the ceiling: a tournament-of-translators with a judging agent usually beats single-pass craft.
- Add a Prosody/Scansion pass (English targets) or Tone/Parallelism pass (Chinese targets)
  - Dedicated agent whose sole job is musicality: syllable balance, stress patterns, internal rhyme/assonance, alliteration density, repetition motifs, punctuation cadence.
- Add a Back-Translation Verifier
  - A bilingual checker back-translates the final into the source language, highlighting additions, omissions, semantic shifts. The reviser must justify any intentional divergence or revise to correct it.
- Add an NLI-style No-Addition/No-Omission check
  - If you can’t run a separate model, add a reasoning pass that explicitly lists suspected content additions/omissions versus source lines. Make the reviser resolve each item or mark intentional.

Prompt-level upgrades: Initial Translation (non-reasoning)
- Reduce “fake research” risk
  - Replace “Research…” steps with “If known, briefly note context; otherwise, identify needed context without inventing.”
- Make the draft structurally aligned to the source
  - Require line-by-line alignment: same stanza count and near-identical line count unless justified. If a line must split/merge, the notes must say why.
- Force a compact “literal gloss” first (in notes)
  - One-line-per-line literal gloss in the notes before the poetic draft. This helps later agents audit meaning without exposing chain-of-thought in the poem body.
- Require 3 opening-line options and 2 full-poem options in the notes (short, not polished)
  - You already ask for this, but outputs aren’t reliably providing it. Enforce with a specific list template in the notes: Opener A/B/C (one-liners), and Full Version 1/2 (each in ≤120% of poem length). The “initial_translation” still only contains the selected best version.
- Add a “Foreignize vs. Domesticate” dial in the system prompt
  - Example: “Set cultural adaptation = Balanced (keep culturally specific items untranslated when musical; avoid explanatory footnotes in poem; add one-line gloss in the notes if required).”
- Add a “No semantic additions unless flagged” rule
  - If the translator adds a word not entailed by the source (e.g., “waits” where the source only wanders), require a bracketed justification in the notes and a second variant without that addition.
- Add a compact musicality brief in the notes
  - Ask for: target rhythm plan (free verse vs loose iambics), repetition strategy (how to mirror source repeats), sound devices (alliteration/assonance choices), punctuation/cadence logic.
- Ban generic filler and over-literal “-like” chains
  - Add a red-flag list: avoid repetitive “like a… like a…” unless the source repeats; replace “X-like” with embedded metaphors or noun-phrase compounds when faithful.

Prompt-level upgrades: Editor Review (reasoning)
- Expand the rubric to a mini scorecard
  - Ask the editor to assign High/Med/Low impact per suggestion and add a 1–10 score per axis (Faithfulness, Fluency, Musicality, Cultural resonance). Keep it brief but numeric: it improves self-consistency and comparability.
- Force Additions/Omissions/Distortions triage
  - First three items must list suspected additions, omissions, and distortions with line references and fixes.
- Require a coverage map at the top (short)
  - One-liner per stanza: “S1 coverage: full; S2: line 3 metaphor weakened; S3: pronoun cohesion…” This helps the reviser focus.
- Musicality prescriptions must be concrete
  - Require the editor to propose actual scans (syllable counts or stress hints) for 2–3 tricky lines and provide minimal pairs showing improved cadence.
- Cultural strategy sanity check
  - Ask for a one-sentence foreignize/domesticate critique: “Keep oil-paper umbrella untranslated; no in-line gloss; move explanation to notes.”
- Alternatives for hard lines
  - Already present; insist on 2 distinct stylistic alternatives (not just synonyms) for each “critical” line.

Prompt-level upgrades: Translator Revision (non-reasoning)
- Add a “No new content” hard gate
  - “Do not introduce new imagery or micro-meanings not licensed by the source. If the editor suggests an addition for musicality, supply two variants: with and without the addition; pick one and justify in notes.”
- Require a final self-audit checklist in the notes
  - Tick: lines/stanzas preserved; repetitions preserved; no additions; key metaphors intact; pronouns consistent; cultural items handled per strategy; cadence read-aloud pass done.
- Add a “Tone calibration” micro-brief
  - One sentence: “Target tone = restrained, lucid, modern lyric; avoid archaism unless source demands.”
- If you change the title or key term, justify with 1–2 alternatives you rejected and why (brief).

Few-shot strategy (yes, but ruthlessly curated)
- Use 3–5 few-shots total, each short, surgical, and labeled by purpose:
  - A symbolist Chinese→English pair showing how to carry repetition, synesthesia, and ambiguity with minimal additions.
  - An English modern lyric→Chinese pair showing balanced domestication (no archaic drift, no over-explanation).
  - A formal-leaning example (loose meter/rhyme) to model prosody without woodenness.
  - A “hard image” case with cultural object retention (e.g., “oil-paper umbrella”) and a one-line gloss in notes.
  - One negative example showing over-interpretation, with a corrected version (this trains restraint).
- Keep few-shots poet-agnostic but style-targeted; avoid long pieces. A 6–10 line excerpt is ideal. The goal is to teach moves, not content.

Faithfulness guardrails (critical to avoiding subtle drift)
- Line-by-line literal gloss in notes (initial translator), then poetic version. This allows systematic auditing without revealing raw chain-of-thought in the poem text.
- Additions/Omissions list mandatory for editor; reviser must settle each item with either a fix or a reasoned exception.
- Back-translation agent to surface semantic leaks; reviser resolves or tags deliberate changes.
- Optional: “Minimize lexical enrichment” constraint—cap the total number of content words that aren’t traceable to the source per stanza unless justified.

Musicality and form upgrades
- A dedicated prosody agent or prompt section with:
  - Syllable balance per line (rough), purposeful variation.
  - Sound-device target: desired alliteration/assonance density per stanza (low/med/high).
  - Repetition mirroring: explicit mapping for repeats (“悠长，悠长” → “long, long—” with cadence plan).
  - Rhyme/echo strategy: slant rhyme locales if used, or internal rhyme anchors.
  - Punctuation cadence: commas vs dashes vs line breaks; justify the pulse.
- For Chinese targets: tone contours and parallelism
  - Encourage parallel couplets, even in free verse; control chengyu/archaism drift; avoid faux-ancient diction unless the source is archaic.

Cultural strategy and terminology
- Explicit “foreignize/domesticate” dial in system prompt with examples of do/don’t.
- Mini glossary per poem in the notes (3–8 items max): key terms, chosen renderings, and what you will not do (e.g., no literal “sigh-like gaze” if a fused compound works better).
- Avoid in-line explanatory glosses in the poem. If a gloss is absolutely needed, keep it in the notes only.

Evaluation and selection (where you catch the last 10%)
- Tournament-of-translators
  - Candidate set from different strategy lanes. Editor critiques each. Judge scores and splices a composite. Reviser polishes. This raised ceilings significantly in practice.
- Blind A/B within the pipeline
  - Have the Judge compare the post-Editor favorite vs. a lightly re-metered variant from Prosody pass. Choose the one with higher musicality without semantic cost.
- Quantitative sanity checks (lightweight)
  - Track repetition preservation rate, line count variance, average syllables per line vs source length, content-word ratio difference, pronoun chain consistency. Don’t overfit; use as alerts.
- Human-in-the-loop spot checks
  - For “hard” poems (dense metaphor, high-culture load), route to a human reviewer with a one-page rubric. Keep it optional.

Concrete prompt snippets you can graft in (adapt wording)
- Initial translator, add to system: “Preserve each stanza and line count unless you provide a compelling reason. In your notes, include a one-line literal gloss per source line, then your chosen poetic rendering. Do not add meanings not entailed by the source; if you propose an addition for musicality, provide an alternative without it and explain.”
- Initial translator, add to user: “In <initial_translation_notes>, include: A) 3 opening-line options; B) 2 full-poem variants (concise), labeled strategy (literal-leaning / balanced / formal); C) a musicality plan; D) a mini glossary of 3–8 items; E) a sentence on foreignize/domesticate choice.”
- Editor, add to system: “Begin with a brief coverage map and a 3-item triage: suspected additions, omissions, distortions (with line refs). For each suggestion, mark Impact (High/Med/Low) and provide two distinct stylistic alternatives for hard lines.”
- Revising translator, add to user: “Implement fixes while avoiding any new semantic additions. If any suggestion introduces meaning, produce two micro-variants and pick one with a rationale. Conclude notes with a self-audit checklist and a read-aloud cadence note.”

Operational considerations
- Model specialization per stage
  - Use your strongest reasoning model for Editor and Judge. Use your most fluent generative model for Candidate Generation and Revision. Keep temperatures higher for candidate generation, lower for revision.
- Temperature choreography
  - Candidate Generation: 0.7–0.9; Editor/Judge: 0.1–0.3; Prosody pass: 0.2–0.4; Final Revision: 0.3–0.5.
- Keep outputs rigidly structured
  - You already enforce XML blocks. Maintain that. For the new stages, define equally strict schemas so downstream parsing is deterministic.

Why this will push the ceiling
- Multiple strategy lanes + a judge consistently outperforms single-pass prompting.
- Literal gloss + no-addition guardrails stop subtle drift while still allowing musical risk-taking (with explicit approval).
- A dedicated prosody pass makes the difference between “accurate” and “sings.”
- The back-translation verifier catches invisible leaks that even strong editors miss.

A few tailored observations from your examples
- The Rain Alley revision added “waits.” It improved music but added meaning. The new prompts would force a no-additions variant and a justification, likely keeping faithfulness tighter while preserving cadence through a different device.
- Your editor is already excellent at line-level fixes; giving them the triage (additions/omissions/distortions) and numeric scoring will make their influence more surgical and consistent.
- Title choices should be treated as a mini-decision with 2–3 alternates and rationale; lock that in as a required note.

A few questions to tailor this further
- Can you add new stages to the pipeline (Candidate Generation, Judge, Prosody, Back-translation), or must you keep T–E–T?
- Are you able to use different models per stage and adjust temperatures?
- Do you want optional formal prosody (meter/rhyme) targets for certain poems, or keep most as free verse with guided cadence?
- Are brief after-poem notes acceptable to your end users, or must all explanations stay outside the poem entirely?
- Do you want a foreignize/domesticate dial exposed as a runtime parameter?

If you share constraints on models, latency, and how many stages you can add, I can turn this into concrete revised YAMLs for each prompt (plus new ones for Candidate, Judge, Prosody, Back-translation) with exact field schemas.