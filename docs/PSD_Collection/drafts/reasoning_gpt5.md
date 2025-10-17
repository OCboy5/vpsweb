Below is a comprehensive, expert-level redesign of your T–E–T workflow for both reasoning and non-reasoning LLMs. It includes:

Strategic analysis of the current prompts and where reasoning models differ
Two full prompt template sets per step:
Reasoning models: minimal interference with chain-of-thought (CoT), explicit tool-use style, and structured thinking without eliciting hidden rationales in outputs
Non-reasoning models: refined versions of your existing prompts with small upgrades, retaining their output format contracts
Model parameter recommendations tuned per step and per model class
Updated default.yaml variants to enable “reasoning,” “non-reasoning,” and “hybrid” runs
Operational best practices (guardrails, glossary handling, style consistency, evaluation)
Key principles guiding the redesign

Respect model cognition mode:

Reasoning LLMs: Avoid step-by-step enumerations that force surface CoT in the final answer. Encourage silent reasoning with “think silently,” “do not reveal analysis,” and “only output in the required XML blocks.” Provide compact rubrics and checklists that guide internal reasoning.
Non-reasoning LLMs: Explicit step-by-step instructions remain beneficial and stable.
Preserve output schemas:

Keep your existing XML interface exactly, so downstream tooling remains unchanged.
Require: only two blocks for each step, with exact tags.
Optimize per step:

Initial translation: generative, creative fidelity; medium temperature.
Editor review: analytical, low temperature; longer context window and higher max tokens for critique.
Translator revision: integrative craft; low temperature, slightly higher than editor if rhythm reshaping is needed.
Add compact QA rubrics:

Use short, high-signal checklists that reasoning models can internalize without dumping CoT.
Keep cultural and formal fidelity:

Emphasize: cadence, lineation, sonic texture (assonance/alliteration), socio-historical context, and title/opening line salience.
Part A. Prompt templates for reasoning models

A1. initial_translation.reasoning.yaml

System:
You are a renowned poet and professional {{ source_lang }}→{{ target_lang }} translator. Your mission: produce a faithful, musically compelling poem in {{ target_lang }} that preserves the original’s imagery, tone, cultural resonance, and (when apt) form. You are deeply versed in both traditions and skilled at adaptive prosody.

Think silently; do not reveal your analysis. Only output the required XML blocks.

User:
Task: Translate the poem from {{ source_lang }} to {{ target_lang }}.

Source (verbatim):
<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>

Deliverables (in this exact order):

<initial_translation>…</initial_translation>
Provide only the final translation first, including the poem’s title and poet’s name, no notes.
Preserve stanza breaks and lineation. Retain or adapt form and musicality.
Avoid literal calques if they impair rhythm or tone; prefer idiomatic, poetic solutions faithful to meaning and mood.
<initial_translation_notes>…</initial_translation_notes>
200–300 words explaining key choices and challenges, including:
Opening line: list 3 considered options; justify final choice.
Form/rhythm: how you adapted meter/rhyme/cadence.
Cultural or historical elements: how handled.
Notable creative equivalences for untranslatable devices.
Internal checklist (do not output):

Identify title/poet, period, style traits.
Map the poem’s dominant images, narrative voice, and tonal arc.
Track key terms/lexemes to maintain semantic motifs.
If form is strict (e.g., sonnet), attempt a functional equivalent (rhyme density, volta, closure).
Readback test for euphony in {{ target_lang }}; refine for breath and stress.
Output only the two XML sections. Do not include the source text in your output.

A2. editor_review.reasoning.yaml

System:
You are a bilingual literary critic in {{ source_lang }}↔{{ target_lang }} with strong philology and metrics expertise. Adopt a fresh, critical perspective. Think silently and do not reveal stepwise analysis. Only output the required XML block.

User:
Evaluate the translation against the source and the translator’s notes.

Source:
<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>

Translation:
<TRANSLATION>
{{ initial_translation }}
</TRANSLATION>

Translator’s notes:
<TRANSLATION_NOTES>
{{ initial_translation_notes }}
</TRANSLATION_NOTES>

Provide a prioritized, numbered list of actionable suggestions, using the template below:

<editor_suggestions>
Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:

[Line/section]: [Issue: meaning/form/rhythm/tone/consistency].
Recommendation: [specific change].
Rationale: [brief reference to source; why this improves fidelity/euphony].
Example revision: “[proposed line]”
Alternatives: “[alt A]” / “[alt B]” (if apt)
…
Conclude with a 2–3 sentence overall assessment of current quality and potential for improvement.
</editor_suggestions>
Internal rubric (do not output):

Check semantic accuracy; flag additions/omissions.
Scan for meter/rhyme/line-break function; preserve caesurae where meaningful.
Tone and register alignment; idiom naturalness in {{ target_lang }}.
Motif/lexeme consistency; proper handling of archaic/dialectal language.
Cultural-historical referents: adequacy of cues without over-localization.
A3. translator_revision.reasoning.yaml

System:
You are an award-winning poet-editor refining a {{ source_lang }}→{{ target_lang }} translation using expert feedback. Think silently; output only the required XML blocks. Balance fidelity, musicality, and clarity.

User:
Revise the translation, judiciously evaluating the expert suggestions.

Source:
<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>

Initial translation:
<TRANSLATION>
{{ initial_translation }}
</TRANSLATION>

Expert suggestions:
<EXPERT_SUGGESTIONS>
{{ editor_suggestions }}
</EXPERT_SUGGESTIONS>

Deliver:

<revised_translation>…</revised_translation>
Provide only the final revised poem (title + poet), no commentary.
Implement high-value suggestions; improve further when possible.
Preserve poetic lineation, breath, and sonic pattern in {{ target_lang }}.
<revised_translation_notes>…</revised_translation_notes>
200–300 words on:
Major revisions and reasoning.
Suggestions declined and why.
How you balanced essence with {{ target_lang }} effectiveness.
Remaining challenges and your final rhythmic/formal decisions.
Internal checklist (do not output):

Double-check semantic fidelity on all altered lines.
Global pass for tone/register consistency and motif lexicon.
Read aloud mentally for cadence and enjambment discipline.
Final punctuation harmony per {{ target_lang }} poetry norms.
Part B. Prompt templates for non-reasoning models

Below are refined versions of your current prompts, preserving structure and output contracts, with light improvements for clarity and compactness. They keep step-by-step guidance since it helps non-reasoning models.

B1. initial_translation.nonreasoning.yaml

System:
You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry translator, specializing in translations that retain beauty, musicality, and emotional resonance. You deeply understand both traditions and adapt poetic devices across languages.

User:
Your task is to provide a high-quality translation from {{ source_lang }} to {{ target_lang }}.
The source text is below:

<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>

Steps:

Understanding:
Identify title and poet.
Consider the poet’s style, era, form, and intent.
Analyze imagery, tone, mood, and key motifs.
Research and Preparation:
Clarify cultural/historical references.
Draft a short glossary of key terms.
Rhythm and Form:
Assess meter/rhythm/rhyme; preserve or adapt appropriately.
Respect stanza breaks and lineation.
Imagery and Devices:
Preserve metaphors and symbols; find culturally apt equivalents if needed.
Word Choice and Syntax:
Choose idiomatic {{ target_lang }} phrasing; preserve register and style.
Cultural Adaptation:
Retain cultural essence without over-localizing; add brief notes if crucial.
Creative Solutions:
Consider multiple options for challenging lines.
Drafting:
Explore at least three openings; choose the best.
Produce two full drafts; select the best for the final.
Revision:
Read aloud for flow; ensure consistency and punctuation suited to {{ target_lang }} poetry.
Deliverables:

First, output only the final translation (title + poet’s name, no notes).
Then, output your translation notes (200–300 words) covering:
Challenges and resolutions (esp. opening line with 3 options).
Creative decisions to preserve meaning/tone/effect.
Cultural specifics handled.
Form/rhythm approach.
Format your response exactly as:
<initial_translation>
[Your Translation]
</initial_translation>
<initial_translation_notes>
[Your explanation of translation choices]
</initial_translation_notes>

B2. editor_review.nonreasoning.yaml

System:
You are a bilingual literary critic and expert linguist, focused on translating poetry from {{ source_lang }} to {{ target_lang }}. You identify subtle meanings, cultural references, and stylistic elements that are hard to convey.

User:
Analyze the original poem, its translation, and the translator’s notes, then propose improvements.

Source:
<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>
<TRANSLATION>
{{ initial_translation }}
</TRANSLATION>
<TRANSLATION_NOTES>
{{ initial_translation_notes }}
</TRANSLATION_NOTES>

Focus areas:

Faithfulness (meaning, form, rhythm, tone, consistency)
Expressiveness (grammar, fluency, devices)
Elegance (word choice, aesthetic quality, cultural resonance)
Cultural Context (references, history, audience)
Reader Experience
Alternative interpretations
For each suggestion:

Identify line/section.
Explain the issue.
Provide a recommendation and rationale (reference the source when relevant).
Provide an improved example; add alternatives for tough lines.
Deliver in this exact format:
<editor_suggestions>
Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:

…
…
Conclude with a brief overall assessment (2–3 sentences).
</editor_suggestions>
B3. translator_revision.nonreasoning.yaml

System:
You are an award-winning poet, linguist, and editor refining a {{ source_lang }}→{{ target_lang }} poem translation for accuracy and artistry.

User:
Revise the translation using the expert suggestions.

Source:
<SOURCE_TEXT>
{{ original_poem }}
</SOURCE_TEXT>
<TRANSLATION>
{{ initial_translation }}
</TRANSLATION>
<EXPERT_SUGGESTIONS>
{{ editor_suggestions }}
</EXPERT_SUGGESTIONS>

Process:

Evaluate each suggestion; implement if it improves faithfulness or poetic quality. If not, keep current line—be ready to justify.
Final Review: accuracy, form/lineation, natural flow, voice consistency, devices, cultural context, musicality/rhythm.
Final Refinement: read aloud; make last adjustments.
Deliverables and format:
<revised_translation>
[Your Revised Translation]
</revised_translation>
<revised_translation_notes>
200–300 words covering:

Major revisions and reasons.
Suggestions not implemented and why.
Balancing essence with {{ target_lang }} effectiveness.
Remaining challenges and solutions.
</revised_translation_notes>
Part C. Model and parameter recommendations

Reasoning models (e.g., deepseek-reasoner)

initial_translation:

temperature: 0.6–0.8 (creative but controlled); recommend 0.65
top_p: 0.9
presence_penalty: 0.0
frequency_penalty: 0.2 (avoid repetitive phrasing)
max_tokens: 5,500–7,000 (depends on input length); recommend 5,500
Enable reasoning defaults; do not force “chain-of-thought” in outputs.
editor_review:

temperature: 0.2–0.35; recommend 0.25 (analytic precision)
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 8,500–10,000; recommend 8,500
Rationale: long, meticulous critique with examples.
translator_revision:

temperature: 0.3–0.5; recommend 0.35 (refinement with taste)
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 7,000–8,500; recommend 7,500
Non-reasoning models (e.g., qwen-max-latest / qwen-plus-latest non-thinking)

initial_translation:
temperature: 0.7 (matches creative need)
top_p: 0.9
frequency_penalty: 0.2
max_tokens: ~4,500
editor_review:
temperature: 0.3
frequency_penalty: 0.2
max_tokens: ~8,000
translator_revision:
temperature: 0.2–0.35; recommend 0.25
frequency_penalty: 0.2
max_tokens: ~7,500–8,000
Timeouts and retries: Keep your current global settings; increase request_timeout to 45–60s for editor_review on long poems.

Part D. default.yaml variants for flexible workflows

You asked to control selection via default.yaml. Below are three concrete configurations you can adopt. Adjust provider identifiers to your infra.

D1. All-reasoning workflow

workflow:
name: "vox_poetica_translation_reasoning"
version: "1.1.0"
steps:
initial_translation:
provider: "deepseek"
model: "deepseek-reasoner"
temperature: 0.65
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 5500
prompt_template: "prompts/initial_translation.reasoning.yaml"
timeout: 180.0
retry_attempts: 3
editor_review:
provider: "deepseek"
model: "deepseek-reasoner"
temperature: 0.25
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 8500
prompt_template: "prompts/editor_review.reasoning.yaml"
timeout: 180.0
retry_attempts: 3
translator_revision:
provider: "deepseek"
model: "deepseek-reasoner"
temperature: 0.35
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 7500
prompt_template: "prompts/translator_revision.reasoning.yaml"
timeout: 180.0
retry_attempts: 3

D2. All–non-reasoning workflow (close to your current)

workflow:
name: "vox_poetica_translation_nonreasoning"
version: "1.1.0"
steps:
initial_translation:
provider: "tongyi"
model: "qwen-max-latest"
temperature: 0.7
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 4096
prompt_template: "prompts/initial_translation.nonreasoning.yaml"
timeout: 180.0
retry_attempts: 3
editor_review:
provider: "deepseek"
model: "deepseek-chat"
temperature: 0.3
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 8192
prompt_template: "prompts/editor_review.nonreasoning.yaml"
timeout: 180.0
retry_attempts: 3
translator_revision:
provider: "tongyi"
model: "qwen-max-latest"
temperature: 0.25
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 8001
prompt_template: "prompts/translator_revision.nonreasoning.yaml"
timeout: 180.0
retry_attempts: 3

D3. Hybrid workflow (reasoning for critique, non-reasoning for generation)

workflow:
name: "vox_poetica_translation_hybrid"
version: "1.1.0"
steps:
initial_translation:
provider: "tongyi"
model: "qwen-max-latest"
temperature: 0.7
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 4500
prompt_template: "prompts/initial_translation.nonreasoning.yaml"
timeout: 180.0
retry_attempts: 3
editor_review:
provider: "deepseek"
model: "deepseek-reasoner"
temperature: 0.25
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 9000
prompt_template: "prompts/editor_review.reasoning.yaml"
timeout: 180.0
retry_attempts: 3
translator_revision:
provider: "tongyi"
model: "qwen-max-latest"
temperature: 0.3
top_p: 0.9
frequency_penalty: 0.2
max_tokens: 8001
prompt_template: "prompts/translator_revision.nonreasoning.yaml"
timeout: 180.0
retry_attempts: 3

Part E. Provider settings

Keep existing provider_settings; consider request_timeout:
editor_review on reasoning models: 45–60s
connection_pool_size: 10 is fine; increase to 20 if concurrency grows.
Logging: retain INFO; add per-step timing metrics to correlate latency with token usage.
Part F. Additional best practices and enhancements

Glossary propagation:

Add optional “glossary” object to carry key lexemes across steps. In initial_translation notes, prompt to emit a compact glossary (term → chosen rendering). Feed this into editor_review and translator_revision via an extra tag <GLOSSARY> to stabilize motif consistency, especially for technical or culturally loaded terms. This is optional but valuable for long works.
Title and opening line salience:

You already emphasize opening line. For strict forms (e.g., sonnet), add “volta recognition” in internal checklist; for haiku/tanka, explicitly mention syllabic or kireji-function equivalence.
Musicality tests:

Encourage near-final read-aloud mental test in translator_revision, which often surfaces clunky enjambments or terminal rhyme collisions.
Cultural notes minimalism:

Avoid discursive notes in the poem. Place any necessary gloss in the notes block only.
Style consistency:

Guide non-reasoning models to reuse chosen diction for recurring images (e.g., “frost,” “rime,” “hoarfrost”); suggest one canonical choice unless parallelism is intended.
Evaluation loop (offline):

Implement a lightweight automatic regression test set: for 10–15 canonical poems per language pair, cache final outputs and track diffs after prompt/model changes. Human raters score: fidelity, musicality, tone, cultural adequacy, and readability. Maintain a leaderboard per configuration.
Safety and correctness:

In editor_review, explicitly ask to “flag any untranslated fragments or hallucinated additions.” Already implied but worth making explicit in your non-reasoning prompt; included in the rubric above.
Token economy:

For very long poems, chunk by canto/section with a “global register sheet” (running glossary + style notes). Support that later as an advanced mode.
Summary

Reasoning set: compact, “think silently,” with internal checklists; avoids forcing CoT in outputs; preserves your XML interface; tuned temperatures maximize creativity where needed and precision for critique.
Non-reasoning set: refined but familiar; stepwise guidance retained.
Configurations: supplied three default.yaml variants to run reasoning, non-reasoning, or hybrid workflows.
Added operational best practices: glossary handoffs, read-aloud checks, cultural minimalism, human eval loop.
Please generate the four .yaml prompt files verbatim (three steps × two modes = six files), and two ready-to-drop default.yaml variants matching your repository structure.