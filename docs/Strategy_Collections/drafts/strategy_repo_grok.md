Draft Strategy for vpsweb Poetry Translation Repository and Local Web UI
This draft strategy outlines decisions for designing, implementing, and integrating a central repository and local Web UI with vpsweb, based on thorough evaluation of approaches. It draws from best practices in database management, metadata handling, Python web frameworks, and translation systems. The focus is on local personal use, with flexibility for future public expansion. The project remains in development, allowing changes to structures. This serves as a basis for the PSD.
Evaluation of Key Approaches
Approaches were assessed for simplicity, scalability, Python compatibility, and integration with vpsweb's modular structure (e.g., workflow.py for orchestration, storage.py for outputs, Pydantic models in translation.py). Sources emphasize SQLite for local apps and Streamlit for AI UIs, while metadata best practices stress standardization.
Table 1: Database Approaches Comparison



































ApproachProsConsDecision RationaleSQLiteLightweight, file-based, built-in Python support, handles thousands of records efficiently.Limited concurrency for future public use.Chosen for local phase; easy migration to PostgreSQL later.File-Based (JSON)Simple, aligns with current vpsweb outputs.Poor querying for classification/searching.Backup option, not primary.DuckDBAnalytical queries on local data.Overkill for structured poetry data.Not selected; SQLite suffices.MongoDB (NoSQL)Flexible for unstructured notes.Requires server setup, unnecessary for local.Rejected for simplicity.
Table 2: Web UI Frameworks Comparison





























FrameworkProsConsDecision RationaleStreamlitRapid prototyping, Python-only, great for AI/data apps with forms and displays.Less customizable for complex backends.Selected for quick local UI; integrates with vpsweb API.GradioSimple ML demos, shareable UIs.More focused on inputs/outputs, less for browsing.Alternative if demo-heavy; Streamlit better for repository access.FlaskFull control, scalable to public site.Requires more code for UI.Future option for expansion; too heavy now.
Table 3: Metadata Best Practices Evaluation





























PracticeDescriptionApplicationSourcesStandardizationDefine core fields (e.g., poet, title, langs).Extend vpsweb's JSON with DB columns.Essential for classification.Consistency/AuditEnforce via schemas, regular checks.Use Pydantic validation.Prevents issues in scaling.SimplicityAvoid duplicates, keep fields minimal.Start with 10-15 fields.Aligns with personal use.
Inspired by translation management systems like Lokalise and Phrase, which centralize assets but are commercial; custom build for niche poetry.
Major Decisions

Repository Design: SQLite database (poetry_repo.db). Schema: OriginalPoems (id, poet, title, original_text, source_lang, metadata_json); Translations (id, poem_id, type [AI/Human], version, translation_text, notes_logs_json, workflow_mode, date, cost, tokens); Comparisons (optional, id, ai_id, human_id, notes). Use poet-first naming in metadata for consistency. Integrate via sqlite3 module for inserts/queries.
Organization: Relational structure for linking AI/human versions. Classification via SQL queries (e.g., by poet/lang). Future search: Add full-text indexing.
Web UI Design: Streamlit app with sections: Translation Runner (form for input, run vpsweb async, store to DB), Human Input (form to add/link translations), Browser (filtered lists, side-by-side comparisons). Local host via streamlit run app.py.
Implementation Tools: Python sqlite3 for DB; Streamlit for UI; Extend vpsweb with db_utils.py for save/load.
vpsweb Modifications: In storage.py, add save_to_db(db_path, result) post-JSON save. Extend Translation models with fields like translation_type: str = "AI", human_translator: Optional[str]. Hook in workflow.py after execute() to call storage. Update config for db_path env var.

Prototype Strategy

Phase 1: Setup SQLite schema/script. Test inserts with vpsweb sample (short_english.txt).
Phase 2: Modify vpsweb storage for DB saves. Build basic Streamlit: Run translation, store, list poems.
Phase 3: Add human form, comparison view. Test with 20 poems, including human entries.
Testing: Pytest for DB ops; manual UI. Validate metadata consistency.
Timeline/Risks: 1 week MVP. Risks: Data migration—use export scripts; Scalability—monitor for thousands.

This strategy ensures seamless integration, leveraging vpsweb's modularity.