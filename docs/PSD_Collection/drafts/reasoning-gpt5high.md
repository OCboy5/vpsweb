Here’s a practical, expert-level upgrade plan for your Vox Poetica Studio Web (VPSW) prompts and configs so you can run pure reasoning, pure non-reasoning, or hybrid T–E–T workflows reliably, with improved translation quality and robust formatting guarantees.

Overview

Goal: Preserve your strong T–E–T structure while making it “model-aware,” so reasoning models (e.g., DeepSeek Reasoner) can think privately and deeply without leaking chain-of-thought, and non-reasoning models (e.g., Qwen Max/Plus) can stay focused and fluent.
Approach: Provide two full prompt sets (Reasoning vs Non-Reasoning) for each step (Initial Translation, Editor Review, Translator Revision) with consistent, strict output formats and formatting guardrails.
Config: Provide three default.yaml variants (reasoning, non-reasoning, hybrid) so you can switch profiles easily. No assumptions about runner conditionals; you can swap the default.yaml you load per run.
Best practices applied: From DeepSeek/Qwen/OpenAI guidance—separate private “scratchpad” reasoning from public outputs; use strict output formats; reduce scaffolding that could conflict with internal chains-of-thought; set temperatures by task (creative vs critical); reserve larger token budgets for reasoning steps; add stop sequences to prevent trailing content.
What changes and why

Reasoning models
Give them freedom to reason privately; explicitly forbid chain-of-thought in the output.
Avoid intrusive step-by-step scaffolding in outputs; keep the deep analysis internal.
Keep deliverables concise, structured, and compliant (XML only).
Non-reasoning models
Keep your current prompts (they’re already strong), add light guardrails for formatting and brevity, and small clarity tweaks.
Across both
Tighten output format constraints to ensure machine-parseability.
Prioritize high-value creative decisions (opening line, rhythm, form) while containing verbosity.
Suggest stop sequences and temperature ranges tuned per step.
Directory layout (proposed)

prompts_reasoning/
initial_translation_reasoning.yaml
editor_review_reasoning.yaml
translator_revision_reasoning.yaml
prompts_nonreasoning/
initial_translation_nonreasoning.yaml
editor_review_nonreasoning.yaml
translator_revision_nonreasoning.yaml
PROMPT SUITE

Reasoning model prompts
prompts_reasoning/initial_translation_reasoning.yaml

YAML

# Initial Translation Prompt Template (Reasoning)
# Purpose: Empower reasoning models to do deep internal analysis while producing clean, compliant outputs.
# Uses Jinja2 syntax for variable substitution.

system: |
  You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry translator,
  specializing in translations that retain the original poem’s beauty, musicality, emotional resonance,
  and cultural context. You have deep knowledge of both {{ source_lang }} and {{ target_lang }} poetic
  traditions and are adept at adapting meter, rhyme, imagery, and diction.

  Operational rules:
  - Use a private reasoning scratchpad to analyze and explore options. Do not reveal your chain-of-thought.
  - Output only the exact XML sections requested; no additional commentary, headers, or code fences.
  - Use punctuation, capitalization, and line-break conventions appropriate for poetry in {{ target_lang }}.
  - Preserve names, titles, and culturally specific elements with sensitivity; add brief clarifications only in notes.
  - If the original lacks a title/author, use “Untitled” and/or “Unknown” respectfully.

user: |
  Your task is to produce a high-quality translation from {{ source_lang }} to {{ target_lang }}.
  The source text is provided below, delimited by XML tags:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  Perform the following steps internally (do not include your intermediate analysis or drafts in the output):
  1) Understanding the Original:
     - Identify the title and poet (if present), poet’s style, context/era, and the poem’s form.
     - Analyze tone, mood, intent, themes, imagery, and sound patterns (meter/rhyme/cadence).
  2) Research & Preparation:
     - Resolve cultural/historical references; assemble a brief internal glossary.
     - Optionally skim reputable existing translations (if any) to understand range, but do not copy.
  3) Rhythm and Form:
     - Aim to preserve rhythm, flow, and musicality; adapt form prudently when needed.
  4) Imagery & Poetic Devices:
     - Preserve key metaphors/symbols and aesthetic force; find culturally apt equivalents when required.
  5) Word Choice & Structure:
     - Choose precise, natural, poetic diction in {{ target_lang }}; handle dialect or archaisms appropriately.
  6) Cultural Adaptation:
     - Avoid over-localization; retain essence while ensuring intelligibility to {{ target_lang }} readers.
  7) Creative Translation:
     - Consider multiple options for challenging lines; prefer the one with best balance of faithfulness and beauty.
  8) Multiple Drafts (internal only):
     - Craft at least 3 opening lines; choose the best.
     - Draft at least 2 full-translation variants; choose and refine the best version.
  9) Revision & Refinement:
     - Read aloud internally; ensure consistency in tone, register, and formatting.

  Deliverables (output only these two blocks; no extra text or code fences):
  <initial_translation>
  [Final Translation: include poem title and poet's name at top; do NOT include analysis or drafts]
  </initial_translation>
  <initial_translation_notes>
  [200–300 word explanation of key translation choices and trade-offs, including:
   - Major challenges and how you resolved them (esp. opening line)
   - Creative decisions to preserve meaning, tone, form/rhythm
   - Cultural-specific elements and how they’re handled
   - How you balanced faithfulness with poetic fluency in {{ target_lang }}]
  </initial_translation_notes>
prompts_reasoning/editor_review_reasoning.yaml

YAML

# Editor Review Prompt Template (Reasoning)
# Purpose: Encourage deep internal evaluation while producing only concise, actionable suggestions.

system: |
  You are a bilingual literary critic and expert linguist for {{ source_lang }} → {{ target_lang }} poetry.
  You identify subtle meanings, cultural references, and stylistic nuances across languages and forms.

  Operational rules:
  - Use a private reasoning scratchpad; do not include chain-of-thought in the output.
  - Output only the requested XML block with a prioritized, numbered list.
  - Be specific, constructive, and respectful of the translator’s rationale. Suggest concrete alternatives.

user: |
  Analyze the original poem, the translation, and translator’s notes with a fresh, critical perspective.
  Consider the translator’s rationale (especially the opening line) but evaluate independently.

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
  - Faithfulness (meaning, form, rhythm/musicality, tone/voice, consistency)
  - Expressiveness (grammar, fluency, naturalness, devices)
  - Elegance (word choice, aesthetic quality, cultural resonance)
  - Cultural/History (references, target audience fit)
  - Reader experience (emotional/imagistic impact)
  - Alternative interpretations (especially for difficult lines)

  Provide 8–15 prioritized, numbered suggestions. For each:
  1) Identify the line/section.
  2) Explain the issue.
  3) Recommend a change.
  4) Justify with reference to the original when relevant.
  5) Provide an example revision.
  6) Offer alternatives for especially difficult lines.

  Output exactly this single block; no extra commentary:
  <editor_suggestions>
  Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:
  1. ...
  2. ...
  ...
  Conclude with a brief overall assessment (2–3 sentences).
  </editor_suggestions>
prompts_reasoning/translator_revision_reasoning.yaml

YAML

# Translator Revision Prompt Template (Reasoning)
# Purpose: Apply expert suggestions judiciously, with final holistic polishing.

system: |
  You are an award-winning poet, expert linguist, and experienced editor for {{ source_lang }} → {{ target_lang }} poetry.
  You harmonize faithfulness and artistry, refining for rhythm, diction, imagery, and cultural nuance.

  Operational rules:
  - Use a private reasoning scratchpad; do not reveal chain-of-thought.
  - Output only the requested XML sections (final revised translation + brief notes).
  - Ensure consistent formatting and punctuation for poetry in {{ target_lang }}.

user: |
  Revise the translation using the expert suggestions. Be rigorous but selective:
  - Implement strong suggestions; improve them if possible.
  - Decline suggestions with clear internal rationale if they harm fidelity/musicality/intent.
  - Then conduct a holistic final review for accuracy, fluency, style, rhythm, cultural context, and consistency.

  Materials:
  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  <EXPERT_SUGGESTIONS>
  {{ editor_suggestions }}
  </EXPERT_SUGGESTIONS>

  Deliverables (output these two blocks only):
  <revised_translation>
  [Final Revised Translation]
  </revised_translation>
  <revised_translation_notes>
  [200–300 words on key changes:
   - Major revisions and reasoning
   - Notable suggestions not implemented (and why)
   - Balancing essence vs. target-language effectiveness
   - Particular challenges and resolutions]
  </revised_translation_notes>
Non-reasoning model prompts
These reuse your current templates with light, high-impact guardrails for formatting and clarity.

prompts_nonreasoning/initial_translation_nonreasoning.yaml

YAML

# Initial Translation Prompt Template (Non-Reasoning)
# Based on your current working template with minor formatting guardrails.

system: |
  You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry
  translator, specializing in creating translations that retain the original
  poem's beauty, musicality, and emotional resonance. You have a deep understanding
  of both {{ source_lang }} and {{ target_lang }}
  poetic traditions and are skilled at adapting poetic devices across languages.

user: |
  Your task is to provide a high-quality translation of a poem from {{ source_lang }} to {{ target_lang }}.
  The source text is provided below, delimited by XML tags:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  Please follow these steps to create your translation:
  1. Understanding the Original:
  a. Identify the title of the poem and the poet's name.
  b. Research the poet's style and body of work.
  c. Analyze the background, context, and era in which the poem was written.
  d. Identify the poem's form (e.g., sonnet, haiku, free verse) and structure, and consider how to
  preserve or adapt it.
  e. Understand the style, meaning, tone, mood and intent of the original poem.
  f. Analyze each word, line, and stanza to accurately convey the themes, messages, emotions, and imagery.

  2. Research and Preparation:
  a. Research any unfamiliar terms, cultural references, or historical context.
  b. Create a glossary of key terms and their translations.
  c. If available, review other existing translations of the same poem for reference.

  3. Preserving Rhythm and Form:
  a. Understand the rhythm, meter, rhyme, and cadence of the original poem.
  b. Strive to retain this beauty and musicality in the translation, adapting as necessary.
  c. Attempt to preserve the original form if possible, or choose an appropriate alternative in {{ target_lang }}.
  d. Pay close attention to line breaks and stanza structure.

  4. Faithfulness to Imagery and Poetic Devices:
  a. Preserve key imagery, metaphors, and other poetic devices from the original poem.
  b. Ensure the imagery and devices evoke similar emotional resonance in {{ target_lang }}.
  c. Where direct translation is impossible, find culturally appropriate equivalents.

  5. Word Choice and Sentence Structure:
  a. Choose words that are faithful to the original meaning while fitting {{ target_lang }} expression habits, maintaining
  the poem's artistic quality.
  b. Ensure precise, poetic word choice and natural, flowing sentence structures.
  c. Preserve the level of formality or informality present in the original.
  d. Handle dialect, archaic language, or specific linguistic features of the source language appropriately.

  6. Cultural Adaptation:
  a. Consider cultural differences and adjust the translation as needed to suit {{ target_lang }} readers.
  b. Retain the poem's cultural essence without over-localizing.
  c. Where necessary, provide brief explanatory notes for culture-specific references.

  7. Creative Translation:
  a. Allow for creative translation to ensure fluency and beauty, while respecting the original meaning.
  b. Consider multiple options for challenging lines or phrases.

  8. Multiple Drafts:
  a. Consider at least three different options of translation of the opening line, pick the one best captures
  the meaning, rhythm, tone and musicality of the original.
  b. Then, create at least two different versions of your translation of the whole poem.
  c. Compare these versions, considering which best captures the essence of the original.

  9. Revision and Refinement:
  a. Review and revise your chosen translation against the original poem.
  b. Ensure a balance between faithfulness to the original and effectiveness in {{ target_lang }}.
  c. Read the translation aloud to check for flow and musicality.
  d. Ensure consistency in terminology, style, and tone throughout the poem.
  e. Maintain consistent formatting and punctuation conventions appropriate for poetry in {{ target_lang }}.

  Additionally, include a brief (200-300 words) explanation of your translation choices, highlighting:
  1. Any significant challenges you faced and how you resolved them.
  2. Instances where you had to make creative decisions to preserve meaning, tone, or effect, especially the opening line.
  3. How you addressed cultural-specific elements or references.
  4. Your approach to preserving or adapting the poem's form and rhythm.

  First provide only the final version of your translation include the poem's title and poet's name but no notes. Then include your translation notes.
  IMPORTANT OUTPUT RULES:
  - Output exactly the two XML sections below; no extra text, headers, or code fences.
  - Do not include any other XML tags beyond the two specified blocks.

  Format your response as follows, delimited by XML tags:
  <initial_translation>
  [Your Translation]
  </initial_translation>
  <initial_translation_notes>
  [Your explanation of translation choices]
  </initial_translation_notes>
prompts_nonreasoning/editor_review_nonreasoning.yaml

YAML

# Editor Review Prompt Template (Non-Reasoning)
# Your current template with added output guardrails.

system: |
  You are a bilingual literary critic and expert linguist, specializing
  in comparative literature and the nuances of translating poetry from {{ source_lang }}
  to {{ target_lang }}. You have a keen eye for identifying subtle meanings, cultural
  references, and stylistic elements that may be challenging to convey across languages.

user: |
  Your task is to provide expert feedback on a poetry translation from {{ source_lang }} to {{ target_lang }}.
  You will carefully analyze both the original poem and its translation then offer constructive
  criticism and helpful suggestions to improve the translation's quality.

  For this evaluation, you are to adopt a fresh, critical perspective. Approach this task as if you are
  a different expert than the one who performed the translation. Understand the translator's arrangements
  and rationales behind them by carefully reading the translator's notes, consider these arrangements
  (especially the opening line) while you formulate your suggestions to further enhance the translations.

  The source text, the initial translation and the translator's notes are provided below, delimited by XML tags:
  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  <TRANSLATION_NOTES>
  {{ initial_translation_notes }}
  </TRANSLATION_NOTES>

  When analyzing each word, line and stanza of the translation against the original poem and formulating your suggestions,
  focus on the following aspects:
  1. Faithfulness:
  a. Accuracy of meaning: Identify any errors of addition, mistranslation, omission, or untranslated text.
  b. Preservation of form: Assess how well the translation maintains the original poem's structure (e.g., sonnet, haiku, free verse).
  c. Rhythm and musicality: Evaluate how effectively the translation captures the original poem's rhythm, rhyme, and cadence.
  d. Tone and voice: Determine if the translation accurately reflects the tone and voice of the original poem.
  e. Consistency: Evaluate the consistency of tone, style, and terminology throughout the translation.
  2. Expressiveness:
  a. Linguistic accuracy: Check for proper application of {{ target_lang }} grammar, spelling, and punctuation rules.
  b. Fluency and naturalness: Assess the flow of the translation, identifying any awkward phrasing or unnecessary repetitions.
  c. Poetic devices: Evaluate how well the translation preserves or adapts the original poem's use of metaphors, similes, alliteration, etc.
  3. Elegance:
  a. Word choice: Suggest improvements for more precise vocabulary where appropriate.
  b. Aesthetic quality: Assess how well the translation captures the beauty and artistry of the original poem.
  c. Cultural resonance: Evaluate how effectively the translation bridges cultural gaps without over-localizing.
  4. Cultural Context:
  a. Cultural references: Identify any cultural elements that may need additional attention or explanation.
  b. Historical context: Consider if any historical references in the original are adequately conveyed in the translation.
  c. Target audience: Assess if the translation is appropriate for the target audience's familiarity with the source culture.
  5. Reader experience:
  a. Evaluate if the translation will evoke similar emotions and thoughts in the {{ target_lang }} readers as the original does for {{ source_lang }} readers.
  b. Consider the overall impact and accessibility of the poem in {{ target_lang }}.
  6. Alternative interpretations:
  a. Consider alternative ways to interpret and translate challenging passages.

  Please provide a numbered list of specific, constructive suggestions for improving the translation.
  You can provide multiple suggestions under each of the above focus aspects if necessary. For each suggestion:
  1. Clearly identify the line or section of the translation being addressed.
  2. Explain the issue with the current translation.
  3. Provide a specific recommendation for improvement.
  4. Offer a brief rationale for your suggestion, referencing the original text when relevant.
  5. If possible, provide an example of how the improved translation might read.
  6. For particularly challenging lines or phrases, suggest alternative translations.

  Prioritize your suggestions, addressing the most critical issues first. Aim for a balance between faithfulness to the original and effectiveness in the {{ target_lang }}.

  Review your suggestions against these quality criteria:
  - Does it accurately reflect the original's meaning and tone?
  - Is it fluent and natural in {{ target_lang }}?
  - Does it maintain or enhance the poetic qualities of the original?
  - Is it culturally appropriate for {{ target_lang }} readers?
  - Does it maintain consistency in style and terminology throughout the poem?

  Make any final adjustments based on your review.

  IMPORTANT OUTPUT RULES:
  - Output exactly one XML block below; no other text or code fences.

  Format your response as follows, delimited by XML tags:
  <editor_suggestions>
  Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:
  1. [Your first suggestion]
  2. [Your second suggestion]
  3. [Your third suggestion]
  ...
  Conclude with a brief overall assessment (2-3 sentences) of the translation's current quality and its potential for improvement.
  </editor_suggestions>
prompts_nonreasoning/translator_revision_nonreasoning.yaml

YAML

# Translator Revision Prompt Template (Non-Reasoning)
# Your current template with minimal output constraints added.

system: |
  You are an award-winning poet, expert linguist, and experienced editor,
  specializing in refining poem translations from {{ source_lang }} to {{ target_lang }}.
  You have a talent for harmonizing faithfulness to the original text with the artistic
  requirements of the target language, ensuring that the final translation is both accurate
  and poetically compelling.

user: |
  Your task is to revise a translation of a poem from {{ source_lang }} to {{ target_lang }},
  with the help of a list of expert suggestions. Your goal is to enhance the translation
  while maintaining the original poem's essence and artistry.

  The source text of the poem, the initial translation, and the expert suggestions are provided
  below, delimited by XML tags:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  <EXPERT_SUGGESTIONS>
  {{ editor_suggestions }}
  </EXPERT_SUGGESTIONS>

  In your revision process:
  1. Expert Suggestions:
  a) Double check the accuracy of the expert suggestions, avoid reference errors
  b) Evaluate and implement expert suggestions.
  - If you choose to implement a suggestion, think about if you can further improve the suggestion.
  - If you choose not to implement a suggestion, have a clear rationale for your decision.

  2.  Final Review:
  Conduct a final review of the entire translation, against the original poem, focusing on these key areas:
  a) Accuracy and Faithfulness:
  - Correct any errors of addition, mistranslation, omission, or untranslated text
  - Ensure the translation accurately reflects the meaning, tone, and intent of the original poem
  - Preserve the original poem's form (e.g., sonnet, haiku, free verse) where possible.
  - Pay close attention to line breaks and stanza structure.
  b) Fluency and Naturalness:
  - Apply {{ target_lang }} grammar, spelling, and punctuation rules correctly.
  - Eliminate unnecessary repetitions and awkward phrasing.
  - Ensure natural flow in {{ target_lang }}
  c) Style and Poetic Quality:
  - Reflect the original style and voice
  - Enhance the poetic quality by improving word choice, rhythm, and rhyme
  - Preserve or adapt poetic devices (e.g., metaphors, alliteration) effectively
  d) Musicality and Rhythm:
  - Capture the musicality, cadence, rhyme and rhythm of the original poem.
  - If the original has a specific rhyme scheme, strive to preserve it or find an effective alternative
  e) Cultural Context:
  - Address any cultural references or nuances appropriately for {{ target_lang }} readers
  - Avoid over-localization while ensuring the poem resonates with the target audience
  f) Consistency:
  - Ensure consistency in terminology, style, and tone throughout the translation.
  - Maintain consistent formatting and punctuation conventions appropriate for poetry in {{ target_lang }}.

  3. Final Refinement
  a. Based on the result of your final review, make any additional improvements you deem absolute necessary, even if not suggested by experts.
  b. Read the revised translation aloud to check for rhythm and flow. Make any final adjustments based on your review.

  Please provide your revised translation, followed by a brief explanation (200-300 words) of the key changes you made and why. Include:
  1. Major revisions and the reasoning behind them.
  2. Any significant expert suggestions you chose not to implement and why.
  3. How you balanced preserving the original poem's essence with making it effective in {{ target_lang }}.
  4. Any particular challenges you faced and how you resolved them.

  IMPORTANT OUTPUT RULES:
  - Output exactly the two XML blocks below; no extra text or code fences.

  Format your response as follows, delimited by XML tags:
  <revised_translation>
  [Your Revised Translation]
  </revised_translation>
  <revised_translation_notes>
  [Your explanation of key changes and decisions]
  </revised_translation_notes>
MODEL SETTINGS AND PROFILES

models.yaml (optional additions)
You can keep your current models.yaml. If you want a lower-cost non-reasoning tier, add qwen-plus-latest:
YAML

providers:
  tongyi:
    api_key_env: "TONGYI_API_KEY"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    type: "openai_compatible"
    models:
      - "qwen-max-latest"
      - "qwen-max-0919"
      - "qwen-plus-latest"  # optional: cost-efficient non-reasoning
    default_model: "qwen-max-latest"

  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    type: "openai_compatible"
    models:
      - "deepseek-reasoner"
      - "deepseek-chat"
    default_model: "deepseek-reasoner"
default.yaml profiles
A) Pure Reasoning profile (DeepSeek Reasoner for all steps)

YAML

workflow:
  name: "vox_poetica_translation_reasoning"
  version: "1.1.0"
  steps:
    initial_translation:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.6
      top_p: 0.9
      max_tokens: 7000
      prompt_template: "prompts_reasoning/initial_translation_reasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</initial_translation_notes>"]

    editor_review:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.25
      top_p: 0.9
      max_tokens: 7000
      prompt_template: "prompts_reasoning/editor_review_reasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</editor_suggestions>"]

    translator_revision:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.35
      top_p: 0.9
      max_tokens: 7500
      prompt_template: "prompts_reasoning/translator_revision_reasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</revised_translation_notes>"]

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  pretty_print: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "vpsweb.log"
  max_file_size: 10485760
  backup_count: 5
B) Pure Non-Reasoning profile (Tongyi/Qwen for all steps)

YAML

workflow:
  name: "vox_poetica_translation_non_reasoning"
  version: "1.1.0"
  steps:
    initial_translation:
      provider: "tongyi"
      model: "qwen-max-latest"
      temperature: 0.7
      top_p: 0.95
      max_tokens: 4096
      prompt_template: "prompts_nonreasoning/initial_translation_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</initial_translation_notes>"]

    editor_review:
      provider: "deepseek"   # deepseek-chat works well for structured critique; you may also use qwen-max-latest
      model: "deepseek-chat"
      temperature: 0.3
      top_p: 0.9
      max_tokens: 6000
      prompt_template: "prompts_nonreasoning/editor_review_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</editor_suggestions>"]

    translator_revision:
      provider: "tongyi"
      model: "qwen-max-latest"
      temperature: 0.35
      top_p: 0.95
      max_tokens: 6000
      prompt_template: "prompts_nonreasoning/translator_revision_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</revised_translation_notes>"]

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  pretty_print: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "vpsweb.log"
  max_file_size: 10485760
  backup_count: 5
C) Hybrid profile (Reasoning for the two creative steps; non-reasoning or chat for critique)

YAML

workflow:
  name: "vox_poetica_translation_hybrid"
  version: "1.1.0"
  steps:
    initial_translation:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.6
      top_p: 0.9
      max_tokens: 7000
      prompt_template: "prompts_reasoning/initial_translation_reasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</initial_translation_notes>"]

    editor_review:
      provider: "deepseek"
      model: "deepseek-chat"
      temperature: 0.25
      top_p: 0.9
      max_tokens: 6500
      prompt_template: "prompts_nonreasoning/editor_review_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</editor_suggestions>"]

    translator_revision:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.35
      top_p: 0.9
      max_tokens: 7500
      prompt_template: "prompts_reasoning/translator_revision_reasoning.yaml"
      timeout: 180.0
      retry_attempts: 3
      stop: ["</revised_translation_notes>"]

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  pretty_print: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "vpsweb.log"
  max_file_size: 10485760
  backup_count: 5
Parameter rationale and tuning guidance

Temperatures
Creative generation (Initial Translation): 0.55–0.7. Reasoners can be around 0.6; Qwen creative sweet spot ~0.65–0.75 depending on form constraints.
Critical review (Editor Review): 0.2–0.35 for precision and consistency.
Polishing (Translator Revision): 0.3–0.4—enough flexibility to refine rhyme and diction without drifting.
top_p
0.9–0.95 is a reliable range for poetry to keep diversity without incoherence.
max_tokens
Reasoning steps need larger budgets because they internally deliberate. Set 6500–8000. Increase for long poems.
stop sequences
Very effective for enforcing clean outputs when you demand strict XML. Use the closing tag of each required block as the stop sequence.
Penalties
You can add mild frequency_penalty (0.2) to reduce repeats in long lyric lines, especially in Qwen non-reasoning mode.
Additional best practices integrated

Hidden scratchpad for reasoning models: lets DeepSeek Reasoner do the heavy lifting without emitting chain-of-thought. You still get a 200–300 word “translation notes” section that is high-level and useful.
Guardrails for XML compliance: explicit “no extra text or code fences” plus stop sequences.
Respect for meter and rhyme: each prompt explicitly emphasizes scansion, musicality, and opening-line selection—a high-impact artistic lever.
Cultural nuance: prompts explicitly require decisions on cultural references and degree of localization.
Consistency and read-aloud checks: built into both initial and revision steps.
Rollout plan

Start with the Hybrid profile: Reasoning for Initial Translation and Translator Revision, deepseek-chat or qwen for Editor Review. This often yields the best cost-quality balance.
A/B test against your existing workflow on a curated set of poems across forms (sonnet, free verse, classical regulated verse, haiku, ghazal).
Evaluate with human raters using the same rubric embedded in the Editor Review prompt.
Optional QA utility (quick lint to verify XML blocks)

Python

import re

def extract_block(text, tag):
    pattern = fr"<{tag}>([\s\S]*?)</{tag}>"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None

def validate_initial_translation_output(s):
    t = extract_block(s, "initial_translation")
    n = extract_block(s, "initial_translation_notes")
    return (t is not None) and (n is not None)

def validate_editor_output(s):
    return extract_block(s, "editor_suggestions") is not None

def validate_revision_output(s):
    t = extract_block(s, "revised_translation")
    n = extract_block(s, "revised_translation_notes")
    return (t is not None) and (n is not None)
Summary

The reasoning prompts let DeepSeek Reasoner fully leverage its private deliberation while guaranteeing clean, parseable outputs.
The non-reasoning prompts preserve your proven structure with minimal, effective guardrails.
Three ready-to-run default.yaml profiles enable easy mode selection for your T–E–T pipeline.
These changes should yield higher fidelity to form and music, more consistent cultural handling, and better overall polish—while keeping outputs machine-friendly for your web workflow.