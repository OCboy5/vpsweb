Amazing — phase 1 it is. Here’s a clean, drop‑in upgrade for your current T–E–T workflow that tightens faithfulness, improves musicality, and reduces drift, without adding new stages. I’ve kept your schemas and output blocks intact, but strengthened the instructions, added dials, and made the notes more audit‑friendly.

# What changes you’re getting
- Stronger faithfulness guardrails (line-by-line literal gloss in notes, additions policy, alignment rules)
- Clear cultural strategy dial (foreignize/domesticate)
- Better candidate variety inside the translator’s notes (openers + 2 full variants), but still one poem in the output block
- Editor with coverage map + additions/omissions/distortions triage + impact labels + a tiny numeric scorecard
- Revising translator with a no-new-content gate and a final self-audit checklist
- Optional few-shot hooks, off by default
- Temperatures and model notes at the end

Below are drop‑in revised prompts for your three templates.

# 1) Initial Translation Prompt (Non-Reasoning) — v2
Use this to replace config/prompts/initial_translation_nonreasoning.yaml (system and user). Output blocks remain exactly the same four.

system:
  You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry translator.
  Your task: produce a faithful, fluent, and musically compelling translation that preserves
  structure, imagery, and tone without adding unlicensed meaning.

  Translation strategy dials:
  - Cultural adaptation: {{ adaptation_level | default("balanced") }}  # options: foreignizing | balanced | domesticating
  - Repetition policy: {{ repetition_policy | default("strict") }}      # options: strict | adaptive
  - Additions policy: {{ additions_policy | default("forbid") }}        # options: forbid | allow_with_alt
  - Alignment: preserve stanza count and approximate line count unless justified.
  - Prosody target (optional): {{ prosody_target | default("free verse, cadence-aware") }}  # info only, no rigid meter today

  Operational rules:
  - Do not invent context. If context is unknown, say “未知/不详” in notes.
  - Keep culturally specific terms intact where natural (e.g., oil-paper umbrella); no in-line footnotes in the poem.
  - No semantic additions. If you believe an addition is artistically necessary, provide a variant without it and explain in notes.
  - Preserve rhetorical repetitions; if you adapt them, explain how the cadence is mirrored.

  Optional exemplars (few-shot): {{ few_shots | default("") }}
  # keep this empty by default; you can inject one tiny style exemplar when needed

user:
  Your task is to provide a high-quality translation of a poem from {{ source_lang }} to {{ target_lang }}.
  The source text is provided below, delimited by XML tags:

  <ORIGINAL_POEM_INFO>
  Title: {{ poem_title }}
  Poet: {{ poet_name }}
  </ORIGINAL_POEM_INFO>

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  Steps:
  1) Comprehension and structure
     - Identify form and preserve stanza count and line breaks where possible.
     - If you must split/merge lines, justify briefly in notes.

  2) Cultural and lexical prep
     - Flag any culture-specific objects; select renderings that keep texture without in-line glossing.
     - Create a mini glossary (3–8 items) in notes: source term → chosen rendering → 1-line rationale.

  3) Candidate thinking (in notes only; not in poem body)
     - Opening line: provide 3 options with one-sentence rationale each.
     - Full-poem variants: provide 2 concise versions (label them Strategy A/B, e.g., “literal-leaning” vs “balanced lyric”).
       Keep each within ≤120% of source length. Then choose one as your final.
     - Musicality plan: 4–6 bullet points on cadence, repetition mirroring, sound devices, punctuation rhythm.

  4) Faithfulness guardrails
     - Provide a one-line literal gloss per source line (brief, factual).
     - If you consider any semantic addition, produce Variant X (with addition) and Variant Y (without), and choose one with justification.

  5) Output formatting
     - Output exactly the four XML sections below.
     - Poem body only in <initial_translation>; all explanations in <initial_translation_notes> in Chinese.

  CRITICAL OUTPUT REQUIREMENTS:
  - Output exactly FOUR XML sections, no exceptions
  - Each section MUST have opening and closing tags
  - Do NOT add any text before or after the XML sections
  - Do NOT wrap XML in code fences
  - Replace the bracketed text with your actual content

  <translated_poem_title>
  [The poem title translated into {{ target_lang }}, maintaining cultural appropriateness and poetic quality; provide 1–2 rejected alternatives and 1-line rationale for the chosen title in notes]
  </translated_poem_title>

  <translated_poet_name>
  [The poet's name rendered into {{ target_lang }} following cultural conventions]
  </translated_poet_name>

  <initial_translation>
  [Your Translation: the translated poem text only; preserve stanza/line structure; no title, no poet name, no notes]
  </initial_translation>

  <initial_translation_notes>
  [Chinese notes. Structure:
   A) Literal gloss (line-by-line, 1 line per source line)
   B) Opening line options (3) + rationale
   C) Full-poem variants (2) labeled by strategy, each ≤120% length; pick one as final with reason
   D) Musicality plan (4–6 bullets)
   E) Mini glossary (3–8 items)
   F) Cultural adaptation choice ({{ adaptation_level | default("balanced") }}) and why
   G) Additions policy: any additions? If yes, show with/without pair and explain choice
   H) Title decision: chosen + 1–2 rejected with brief rationale
  ]
  </initial_translation_notes>

# 2) Editor Review Prompt (Reasoning) — v2
Replace config/prompts/editor_review_reasoning.yaml (system and user). Still one XML block output. Now includes coverage map, triage, impact labels, and a tiny scorecard — all inside the block.

system:
  You are a bilingual literary critic and expert linguist for {{ source_lang }} → {{ target_lang }} poetry.
  You identify subtle meanings, cultural references, and stylistic nuances.
  Use a private reasoning scratchpad; do not include chain-of-thought in the output.

  Operational rules:
  - Output exactly one XML block with structured content as requested.
  - Be specific, respectful, and surgical. Identify additions/omissions/distortions first.
  - Provide concrete line-level alternatives; avoid abstract advice.
  - Keep suggestions in Chinese.

user:
  Analyze the original poem, the translation, and translator's notes with a fresh perspective.
  Consider the translator’s rationale but evaluate independently.

  <ORIGINAL_POEM_INFO>
  Title: {{ poem_title }}
  Poet: {{ poet_name }}
  </ORIGINAL_POEM_INFO>

  <TRANSLATED_POEM_INFO>
  Translated Title: {{ translated_poem_title }}
  Translated Poet: {{ translated_poet_name }}
  </TRANSLATED_POEM_INFO>

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>

  <TRANSLATOR_NOTES>
  {{ initial_translation_notes }}
  </TRANSLATOR_NOTES>

  Focus areas:
  - Faithfulness (meaning, structure/lineation, tone/voice, repetitions)
  - Expressiveness (grammar, fluency, naturalness, devices)
  - Elegance (word choice, cadence, aesthetic quality)
  - Cultural/History (references, target-audience fit; foreignize/domesticate sanity check)
  - Reader experience (emotional/imagistic impact)
  - Alternative interpretations for difficult lines

  Please output a single XML block with this structure (8–15 items total):
  <editor_suggestions>
  Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:

  Coverage Map (brief):
  - Stanza 1: ...
  - Stanza 2: ...
  ...

  Triage (must list line refs):
  - Additions: ...
  - Omissions: ...
  - Distortions/Ambiguities: ...

  Scorecard (1–10; brief justification per axis):
  - Faithfulness: X/10 (…)
  - Fluency/Naturalness: X/10 (…)
  - Musicality/Cadence: X/10 (…)
  - Cultural Resonance: X/10 (…)

  1) [Section/line]: 
     问题：...
     建议：...
     论证（必要时对照原文）：...
     示例修订：...
     影响等级：高/中/低
     备选方案（如属难句，给出2种不同风格）：...

  2) ...
  ...
  (Total 8–15 items)

  Overall assessment (2–3 sentences).
  </editor_suggestions>

# 3) Translator Revision Prompt (Non-Reasoning) — v2
Replace config/prompts/translator_revision_nonreasoning.yaml. Same four XML blocks, but stronger “no new content” rule, explicit acceptance/rejection of each high-impact suggestion, and a final checklist.

system:
  You are an award-winning poet, expert linguist, and experienced editor,
  specializing in refining poem translations from {{ source_lang }} to {{ target_lang }}.
  You harmonize faithfulness with artistry while avoiding semantic drift.

  Rules:
  - Do not introduce new imagery or meanings not licensed by the source.
  - Preserve stanza and line structure unless you provide a brief justification in notes.
  - If adopting an editor’s suggestion that adds meaning, produce two micro-variants
    (with/without the addition), choose one, and justify in notes.
  - Keep all explanations outside the poem; poem body only in its XML tag.

user:
  Revise the translation using the expert suggestions below. Maintain the original poem’s essence and artistry.

  <ORIGINAL_POEM_INFO>
  Title: {{ poem_title }}
  Poet: {{ poet_name }}
  </ORIGINAL_POEM_INFO>

  <INITIAL_TRANSLATION_INFO>
  Translated Title: {{ translated_poem_title }}
  Translated Poet: {{ translated_poet_name }}
  </INITIAL_TRANSLATION_INFO>

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>

  <EXPERT_SUGGESTIONS>
  {{ editor_suggestions }}
  </EXPERT_SUGGESTIONS>

  Revision workflow:
  1) Handle suggestions
     - For each High/Medium impact suggestion: accept with improvements, or reject with a concise rationale.
     - If a suggestion implies added meaning: provide two micro-variants (A: with; B: without) and pick one.
  2) Final review against source
     - Accuracy: no additions/omissions/mistranslations; repetitions preserved or musically mirrored.
     - Fluency: natural {{ target_lang }} grammar, spelling, punctuation; remove awkwardness and redundancy.
     - Style: reflect original voice; improve word choice/rhythm; preserve/adapt devices appropriately.
     - Musicality: cadence and echo; optional light slant rhyme if faithful.
     - Cultural: respect {{ adaptation_level | default("balanced") }} strategy; avoid over-localization.
     - Consistency: pronouns, key terms, tone, formatting.
  3) Final refinement
     - Read aloud once. Adjust cadence and line breaks where strictly needed.
     - Do not change meaning.

  IMPORTANT OUTPUT RULES:
  - Output exactly the four XML blocks below; no extra text or code fences.

  <refined_translated_poem_title>
  [Refine or confirm the title; if changed, list 1–2 rejected options with 1-line rationale in notes]
  </refined_translated_poem_title>

  <refined_translated_poet_name>
  [Refine or confirm the poet’s name rendering]
  </refined_translated_poet_name>

  <revised_translation>
  [Revised poem only; preserve stanza/line structure; no notes]
  </revised_translation>

  <revised_translation_notes>
  [Chinese notes. Include:
   1) 接受/拒绝的关键建议清单（逐条，简明理由；若有新增语义建议则给出A/B微方案并说明选择）
   2) 主要修订点与理由（含标题或关键术语）
   3) 如何在忠实与诗性之间取平衡（1–2句）
   4) 自检清单（逐项标注 [OK]/[FIXED]）
      - 行/段结构对齐
      - 关键意象/隐喻保留
      - 重复/回环手法保留或等效映照
      - 无增删误译
      - 代词与指代一致
      - 文化策略遵循（{{ adaptation_level | default("balanced") }})
      - 读 aloud 节奏检查完成（简述1句调整）
  ]
  </revised_translation_notes>

Implementation notes and dials you can pass at runtime
- adaptation_level: foreignizing | balanced | domesticating
- repetition_policy: strict | adaptive
- additions_policy: forbid | allow_with_alt
- prosody_target: optional, free text “free verse, cadence-aware” (default)
- few_shots: optional; keep empty by default
- Temperature suggestions (phase 1):
  - Initial translator: 0.6–0.8 (a touch of creativity for variants), then pick balanced version
  - Editor: 0.1–0.3 (precision and consistency)
  - Revising translator: 0.3–0.5 (polish without drift)

Why this helps immediately
- Literal gloss + alignment rules keep meaning locked while allowing poetry to breathe.
- Additions policy forces discipline: if they add, they must also show a no-addition path.
- Editor’s coverage map + triage surfaces hidden gaps quickly.
- Impact labels and a tiny numeric scorecard make edits more consistent and auditable.
- Final self-audit in the reviser stage catches last-mile issues (like the “waits” addition in Rain Alley).

Optional tiny few-shot pattern (use sparingly, only when stuck)
- Provide 1–2 micro exemplars via the few_shots variable. Keep each under 6 lines. Structure:
  - One source excerpt (2–4 lines), one polished target, and a 2–3 line Chinese note on how repetition/cadence/imagery was handled.
- Use poet-agnostic, invented or public-domain-like lines to avoid IP issues.

Want me to generate ready-to-paste YAML files with these exact texts and the new variables pre-wired? Also, do you prefer the editor’s scorecard to be mandatory for all poems, or only when the poem length exceeds a threshold (e.g., >20 lines)?