# VPSWeb Metadata Standards & Digital Humanities Best Practices

**Supplementary Document to Strategy**  
**Version**: 1.0  
**Date**: October 17, 2025

---

## 1. Introduction

This supplementary document provides research-based recommendations for implementing metadata standards and digital humanities best practices in the VPSWeb poetry translation repository. These recommendations are based on established standards in digital humanities, literary databases, and cultural heritage preservation.

---

## 2. Metadata Standards for Poetry Translation

### 2.1 Core Standards to Consider

#### 2.1.1 Dublin Core (Recommended Foundation)
Dublin Core is a simple yet effective element set for describing networked resources, consisting of fifteen core elements that are optional and repeatable.

**Advantages for VPSWeb**:
- Simple to implement and understand
- Widely adopted across digital humanities
- Extensible with qualifiers
- Language-neutral and cross-cultural
- Supports interoperability

**15 Core Elements**:
1. **Title** - Poem title
2. **Creator** - Original poet
3. **Subject** - Themes, topics
4. **Description** - Abstract or summary
5. **Publisher** - Translation publisher (if applicable)
6. **Contributor** - Translator (human or AI model)
7. **Date** - Creation/translation date
8. **Type** - Resource type (e.g., "Poetry", "Translation")
9. **Format** - MIME type or file format
10. **Identifier** - Unique ID (UUID, DOI)
11. **Source** - Original work reference
12. **Language** - ISO language codes
13. **Relation** - Related resources
14. **Coverage** - Temporal/spatial coverage
15. **Rights** - Copyright/license info

**Recommended Implementation for VPSWeb**:
```python
# Dublin Core mapping to VPSWeb schema
class DublinCoreMetadata(BaseModel):
    # Required
    dc_title: str  # Poem title
    dc_creator: str  # Original poet
    dc_language: str  # ISO 639 code (en, zh, etc.)
    dc_type: str = "Text/Poetry"
    
    # Highly Recommended
    dc_contributor: List[str]  # Translators
    dc_date: datetime  # Translation date
    dc_identifier: str  # UUID or URI
    dc_source: Optional[str]  # Source work citation
    
    # Optional but Valuable
    dc_subject: List[str]  # Themes/keywords
    dc_description: Optional[str]  # Brief description
    dc_format: str = "text/plain"
    dc_relation: List[str]  # Related translations
    dc_rights: Optional[str]  # License
    dc_coverage: Optional[str]  # Time period, location
    dc_publisher: Optional[str]  # If published
```

#### 2.1.2 TEI (Text Encoding Initiative)
TEI is most commonly used for literary texts or manuscripts in digital humanities.

**When to Use TEI**:
- If you need to encode structural elements of poems (stanzas, lines, rhyme schemes)
- For scholarly editions with critical apparatus
- When preserving original formatting is critical
- Future expansion to include manuscript facsimiles

**Recommendation**: Start with Dublin Core for metadata, consider TEI for future text encoding needs.

### 2.2 Extended Metadata Schema for Poetry

Based on digital humanities research, here's a comprehensive metadata schema:

```python
class PoemMetadata(BaseModel):
    """Comprehensive poem metadata following DH best practices"""
    
    # ===== Core Bibliographic (Dublin Core based) =====
    title: str
    author: str
    language: str  # ISO 639-3 code
    identifier: str  # UUID
    date_created: Optional[datetime]
    date_published: Optional[datetime]
    
    # ===== Literary Classification =====
    form: Optional[str]  # sonnet, haiku, ballad, free verse, etc.
    meter: Optional[str]  # iambic pentameter, etc.
    rhyme_scheme: Optional[str]  # ABAB, etc.
    stanza_structure: Optional[str]  # quatrains, tercets, etc.
    line_count: Optional[int]
    
    # ===== Historical/Cultural Context =====
    period: Optional[str]  # Tang Dynasty, Victorian, Modernist, etc.
    movement: Optional[str]  # Romanticism, Imagism, etc.
    cultural_context: Optional[str]
    geographic_origin: Optional[str]
    
    # ===== Thematic =====
    themes: List[str] = []  # love, nature, death, war, etc.
    emotions: List[str] = []  # joy, melancholy, anger, etc.
    symbols: List[str] = []  # rose, moon, bird, etc.
    
    # ===== Intertextuality =====
    allusions: List[str] = []  # References to other works
    influences: List[str] = []  # Influenced by...
    source_text: Optional[str]  # If translation or adaptation
    
    # ===== Rights & Provenance =====
    copyright_status: Optional[str]  # public domain, copyrighted
    license: Optional[str]  # CC-BY, etc.
    source_citation: Optional[str]
    digitization_source: Optional[str]
    
    # ===== Computational =====
    word_count: Optional[int]
    unique_words: Optional[int]
    lexical_diversity: Optional[float]
    sentiment_score: Optional[float]
    reading_level: Optional[str]

class TranslationMetadata(BaseModel):
    """Translation-specific metadata"""
    
    # ===== Translation Identity =====
    translation_id: str
    poem_id: str
    target_language: str
    translator_type: str  # 'ai' or 'human'
    translator_name: str
    translation_date: datetime
    
    # ===== Translation Approach =====
    translation_strategy: Optional[str]  # literal, free, adaptive, etc.
    translation_notes: Optional[str]
    challenges_encountered: List[str] = []
    
    # ===== For AI Translations =====
    workflow_mode: Optional[str]  # reasoning, non_reasoning, hybrid
    ai_model_primary: Optional[str]
    ai_model_editor: Optional[str]
    prompt_version: Optional[str]
    
    # ===== Quality Metrics =====
    quality_score: Optional[float]
    fluency_score: Optional[float]
    adequacy_score: Optional[float]
    human_evaluation: Optional[str]
    
    # ===== Computational Metrics =====
    tokens_used: Optional[int]
    cost_rmb: Optional[float]
    processing_time: Optional[float]
    
    # ===== Comparative =====
    preserves_form: Optional[bool]
    preserves_meter: Optional[bool]
    preserves_rhyme: Optional[bool]
    cultural_adaptation_level: Optional[str]  # minimal, moderate, extensive
```

---

## 3. Controlled Vocabularies & Taxonomies

### 3.1 Poetry Forms (Controlled List)
```python
POETRY_FORMS = [
    # Western Forms
    "sonnet", "ballad", "ode", "elegy", "epic", "lyric",
    "free verse", "blank verse", "haiku", "limerick", "villanelle",
    "sestina", "pantoum", "ghazal", "rondeau", "triolet",
    
    # Chinese Forms
    "绝句 (jueju)", "律诗 (lüshi)", "词 (ci)", "曲 (qu)", 
    "古体诗 (guti shi)", "近体诗 (jinti shi)",
    
    # Other
    "prose poem", "concrete poetry", "visual poetry", "spoken word",
    "other", "unknown"
]
```

### 3.2 Literary Periods
```python
LITERARY_PERIODS = [
    # Western
    "Classical Antiquity", "Medieval", "Renaissance", 
    "Baroque", "Enlightenment", "Romantic", "Victorian",
    "Modernist", "Postmodernist", "Contemporary",
    
    # Chinese
    "Pre-Qin", "Han Dynasty", "Six Dynasties",
    "Tang Dynasty", "Song Dynasty", "Yuan Dynasty",
    "Ming Dynasty", "Qing Dynasty", "Republican Era",
    "Contemporary Chinese",
    
    # Movements
    "Imagism", "Symbolism", "Surrealism", "Beat Generation",
    "Confessional", "Language Poetry", "Misty Poetry (朦胧诗)"
]
```

### 3.3 Themes & Subjects
```python
THEME_TAXONOMY = {
    "nature": ["landscape", "seasons", "plants", "animals", "weather"],
    "human_experience": ["love", "loss", "death", "birth", "aging"],
    "emotions": ["joy", "sorrow", "anger", "fear", "longing"],
    "society": ["war", "politics", "justice", "poverty", "class"],
    "philosophy": ["existence", "time", "memory", "identity", "truth"],
    "spirituality": ["religion", "mysticism", "transcendence", "faith"],
    "art_creativity": ["poetry", "music", "painting", "craft"],
    "relationships": ["family", "friendship", "romance", "solitude"]
}
```

### 3.4 Translation Strategies
```python
TRANSLATION_STRATEGIES = [
    "literal",        # Word-for-word translation
    "faithful",       # Preserves meaning closely
    "semantic",       # Focus on meaning over form
    "communicative",  # Natural in target language
    "free",          # Substantial interpretation
    "adaptive",      # Cultural adaptation
    "transcreation", # Creative reimagining
    "imitation",     # Inspired by, not direct translation
]
```

---

## 4. Data Quality & Validation

### 4.1 Metadata Quality Criteria

Based on digital humanities best practices:

1. **Completeness**: Ensure core fields are populated
2. **Consistency**: Use controlled vocabularies
3. **Accuracy**: Verify factual information
4. **Uniqueness**: Avoid duplicate entries
5. **Provenance**: Track metadata source and changes

### 4.2 Validation Rules

```python
class MetadataValidator:
    """Validate metadata quality"""
    
    REQUIRED_FIELDS = ['title', 'author', 'language', 'original_text']
    RECOMMENDED_FIELDS = ['form', 'period', 'themes', 'date_created']
    
    def validate_completeness(self, poem: Poem) -> dict:
        """Check metadata completeness"""
        score = 0
        max_score = len(self.REQUIRED_FIELDS) + len(self.RECOMMENDED_FIELDS)
        
        # Check required
        for field in self.REQUIRED_FIELDS:
            if getattr(poem, field):
                score += 1
                
        # Check recommended
        for field in self.RECOMMENDED_FIELDS:
            if getattr(poem, field):
                score += 1
                
        return {
            'completeness_score': score / max_score,
            'missing_required': [f for f in self.REQUIRED_FIELDS 
                                if not getattr(poem, f)],
            'missing_recommended': [f for f in self.RECOMMENDED_FIELDS 
                                   if not getattr(poem, f)]
        }
    
    def validate_language_code(self, lang: str) -> bool:
        """Validate ISO 639 language code"""
        # Implementation using pycountry or langcodes library
        pass
    
    def validate_controlled_vocabulary(self, field: str, value: str) -> bool:
        """Check if value is in controlled vocabulary"""
        vocabularies = {
            'form': POETRY_FORMS,
            'period': LITERARY_PERIODS,
            'strategy': TRANSLATION_STRATEGIES
        }
        
        if field in vocabularies:
            return value in vocabularies[field]
        return True  # No validation needed
```

---

## 5. Search & Discovery Features

### 5.1 Full-Text Search Implementation

**SQLite FTS5 Configuration**:
```sql
-- Create full-text search virtual table
CREATE VIRTUAL TABLE poems_fts USING fts5(
    title, 
    author, 
    original_text,
    themes,
    content='poems',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER poems_ai AFTER INSERT ON poems BEGIN
    INSERT INTO poems_fts(rowid, title, author, original_text, themes)
    VALUES (new.id, new.title, new.author, new.original_text, new.themes);
END;

CREATE TRIGGER poems_ad AFTER DELETE ON poems BEGIN
    DELETE FROM poems_fts WHERE rowid = old.id;
END;

CREATE TRIGGER poems_au AFTER UPDATE ON poems BEGIN
    UPDATE poems_fts SET 
        title = new.title,
        author = new.author,
        original_text = new.original_text,
        themes = new.themes
    WHERE rowid = new.id;
END;
```

### 5.2 Advanced Search Features

```python
class SearchService:
    """Advanced search capabilities"""
    
    def search(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        facets: List[str] = None,
        sort_by: str = "relevance"
    ) -> SearchResults:
        """
        Multi-faceted search with filtering
        
        Args:
            query: Full-text search query
            filters: {
                'language': ['en', 'zh'],
                'period': ['Tang Dynasty', 'Romantic'],
                'form': ['sonnet', 'haiku'],
                'date_range': (start_date, end_date),
                'translator_type': 'ai' or 'human',
                'themes': ['love', 'nature']
            }
            facets: ['language', 'period', 'form'] - return counts
            sort_by: 'relevance', 'date', 'author', 'title'
        """
        pass
    
    def similar_poems(self, poem_id: int, limit: int = 10):
        """Find similar poems based on content and metadata"""
        # Use TF-IDF or embeddings for similarity
        pass
    
    def suggest_tags(self, text: str) -> List[str]:
        """Auto-suggest tags based on poem content"""
        # Use NLP to extract themes, emotions, etc.
        pass
```

### 5.3 Faceted Navigation

Implement faceted search interface:

```
┌─────────────────────────────────────────────────┐
│ Search: "spring rain"              [Search]      │
├─────────────────────────────────────────────────┤
│ Filters:                        │ Results (45)   │
│                                 │                │
│ ☐ Language                      │ 1. "Spring..."│
│   ☑ English (23)                │    by Li Bai  │
│   ☑ Chinese (15)                │    Tang D.    │
│   ☐ Japanese (7)                │    [View]     │
│                                 │                │
│ ☐ Period                        │ 2. "Rain..."  │
│   ☐ Tang Dynasty (18)           │    by Basho   │
│   ☐ Romantic (12)               │    Edo        │
│   ☐ Contemporary (15)           │    [View]     │
│                                 │                │
│ ☐ Form                          │ 3. ...        │
│   ☐ Haiku (8)                   │                │
│   ☐ Free Verse (22)             │                │
│   ☐ Sonnet (5)                  │                │
│                                 │                │
│ ☐ Themes                        │                │
│   ☐ Nature (32)                 │                │
│   ☐ Seasons (28)                │                │
│   ☐ Renewal (12)                │                │
└─────────────────────────────────────────────────┘
```

---

## 6. Export Formats & Interoperability

### 6.1 Standard Export Formats

**JSON-LD (Linked Data)**:
```json
{
  "@context": {
    "dc": "http://purl.org/dc/terms/",
    "vps": "http://vpsweb.org/vocab/"
  },
  "@type": "CreativeWork",
  "dc:title": "A Red, Red Rose",
  "dc:creator": "Robert Burns",
  "dc:language": "en",
  "dc:date": "1794",
  "vps:form": "ballad",
  "vps:themes": ["love", "romance", "nature"],
  "vps:translations": [
    {
      "@type": "Translation",
      "dc:language": "zh",
      "dc:contributor": "vpsweb-hybrid-v1.0",
      "vps:translatorType": "ai"
    }
  ]
}
```

**Dublin Core XML**:
```xml
<?xml version="1.0"?>
<metadata
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:title>A Red, Red Rose</dc:title>
  <dc:creator>Robert Burns</dc:creator>
  <dc:language>en</dc:language>
  <dc:date>1794</dc:date>
  <dc:type>Text</dc:type>
  <dc:format>text/plain</dc:format>
  <dcterms:extent>16 lines</dcterms:extent>
</metadata>
```

**CSV for Analysis**:
```csv
id,title,author,language,form,period,themes,translation_count,avg_cost
1,"A Red, Red Rose","Robert Burns","en","ballad","Romantic","love;nature",3,0.000015
```

### 6.2 API Endpoints for Interoperability

```python
# RESTful API following best practices
GET  /api/v1/poems/{id}/metadata              # JSON-LD by default
GET  /api/v1/poems/{id}/metadata?format=dc    # Dublin Core XML
GET  /api/v1/poems/{id}/metadata?format=tei   # TEI Header
GET  /api/v1/poems/export?format=csv          # Bulk export
```

---

## 7. Versioning & Provenance

### 7.1 Metadata Versioning

Track changes to metadata over time:

```python
class MetadataVersion(BaseModel):
    id: int
    poem_id: int
    version_number: int
    metadata_snapshot: dict
    changed_by: str
    change_date: datetime
    change_reason: Optional[str]

# Track what changed
class MetadataChange(BaseModel):
    version_id: int
    field_name: str
    old_value: Any
    new_value: Any
```

### 7.2 Provenance Tracking

Document metadata source and authority:

```python
class MetadataProvenance(BaseModel):
    field_name: str
    source: str  # "user_input", "auto_extracted", "ai_generated", "imported"
    confidence: float  # 0.0-1.0
    evidence: Optional[str]
    verified_by: Optional[str]
    verified_date: Optional[datetime]

# Example
poem.metadata_provenance = {
    'author': MetadataProvenance(
        field_name='author',
        source='user_input',
        confidence=1.0,
        verified_by='editor',
        verified_date=datetime.now()
    ),
    'period': MetadataProvenance(
        field_name='period',
        source='ai_generated',
        confidence=0.85,
        evidence='Based on language patterns and historical context'
    )
}
```

---

## 8. Accessibility & Multilingual Support

### 8.1 Multilingual Metadata

Support metadata in multiple languages:

```python
class MultilingualField(BaseModel):
    en: Optional[str]
    zh: Optional[str]
    # Add more as needed
    
class PoemMetadataMultilingual(BaseModel):
    title: MultilingualField
    description: MultilingualField
    
# Example
poem = PoemMetadataMultilingual(
    title=MultilingualField(
        en="The Journey",
        zh="旅程"
    ),
    description=MultilingualField(
        en="A reflection on life's path",
        zh="对人生道路的思考"
    )
)
```

### 8.2 Accessibility Features

- Alt text for visual elements
- Screen reader compatibility
- Keyboard navigation
- ARIA labels
- High contrast mode
- Text resizing

---

## 9. Integration with Digital Humanities Tools

### 9.1 Compatible Tools

**Text Analysis**:
- Voyant Tools (word clouds, frequency analysis)
- AntConc (concordance, collocation)
- NLTK/spaCy (computational analysis)

**Visualization**:
- Gephi (network graphs of influences)
- Timeline.js (temporal visualization)
- Palladio (geographic mapping)

**Publishing**:
- Scalar (multimedia presentations)
- Omeka (digital exhibitions)
- TEI Publisher (scholarly editions)

### 9.2 Export for Analysis

```python
def export_for_voyant(poems: List[Poem]) -> str:
    """Export corpus for Voyant Tools"""
    corpus = []
    for poem in poems:
        doc = f"""
        <text>
            <title>{poem.title}</title>
            <author>{poem.author}</author>
            <date>{poem.date_created}</date>
            {poem.original_text}
        </text>
        """
        corpus.append(doc)
    return f"<corpus>{''.join(corpus)}</corpus>"

def export_for_gephi(translation_network) -> str:
    """Export translation relationships as graph"""
    # Generate nodes (poets, translators) and edges (translations)
    pass
```

---

## 10. Implementation Recommendations

### 10.1 Phase 1: Core Metadata
1. Implement Dublin Core fields
2. Add poetry-specific fields (form, meter, themes)
3. Basic controlled vocabularies
4. SQLite FTS5 for search

### 10.2 Phase 2: Enhanced Features
1. Metadata validation
2. Auto-tagging with NLP
3. Similarity search
4. Faceted navigation

### 10.3 Phase 3: Advanced DH Integration
1. JSON-LD export
2. TEI encoding support
3. IIIF for image manuscripts
4. OAI-PMH for harvesting

### 10.4 Phase 4: Scholarly Features
1. Versioning system
2. Provenance tracking
3. Citation generation
4. Annotation support

---

## 11. Citation & Bibliography Standards

### 11.1 Automatic Citation Generation

```python
class CitationGenerator:
    """Generate citations in various formats"""
    
    def mla(self, poem: Poem, translation: Translation = None):
        """Modern Language Association format"""
        if translation:
            return f'{poem.author}. "{poem.title}." Trans. {translation.translator_name}. VPSWeb Repository, {translation.translation_date.year}.'
        return f'{poem.author}. "{poem.title}." {poem.date_created.year if poem.date_created else "n.d."}.'
    
    def apa(self, poem: Poem, translation: Translation = None):
        """American Psychological Association format"""
        pass
    
    def chicago(self, poem: Poem, translation: Translation = None):
        """Chicago Manual of Style format"""
        pass
    
    def bibtex(self, poem: Poem):
        """BibTeX format for LaTeX"""
        return f"""
        @poem{{{poem.identifier},
          author = {{{poem.author}}},
          title = {{{poem.title}}},
          year = {{{poem.date_created.year if poem.date_created else ''}}},
          language = {{{poem.language}}},
          url = {{https://vpsweb.org/poems/{poem.id}}}
        }}
        """
```

### 11.2 Persistent Identifiers

Consider implementing:
- **DOIs** (Digital Object Identifiers) - for published works
- **ORCIDs** - for translator identification
- **ARKs** (Archival Resource Keys) - persistent URLs
- **Handles** - for long-term resource location

---

## 12. Quality Assurance Checklist

**Before Each Release**:
- [ ] All required metadata fields populated
- [ ] Controlled vocabulary terms validated
- [ ] Language codes conform to ISO 639
- [ ] Dates in ISO 8601 format
- [ ] No duplicate entries
- [ ] FTS index up to date
- [ ] Export formats tested
- [ ] Citation generators working
- [ ] Search results relevant
- [ ] Metadata internally consistent

---

## 13. Further Resources

### Standards Documentation
- Dublin Core: https://www.dublincore.org/
- TEI Guidelines: https://tei-c.org/
- ISO 639 Language Codes: https://www.loc.gov/standards/iso639-2/
- JSON-LD: https://json-ld.org/

### Digital Humanities Centers
- Digital Humanities at Princeton
- Stanford Literary Lab
- UCLA Digital Humanities
- DHARMA (Digital Humanities Advanced Research Methods Association)

### Tools & Libraries
- `pycountry` - ISO standards (languages, countries)
- `langdetect` - Language identification
- `rdflib` - RDF/Linked Data
- `lxml` - XML processing
- `spacy` - NLP for auto-tagging

---

## 14. Conclusion

Implementing these metadata standards and digital humanities best practices will ensure that VPSWeb:

1. **Interoperates** with other DH projects and tools
2. **Preserves** cultural and linguistic heritage properly
3. **Enables** sophisticated search and analysis
4. **Supports** scholarly citation and research
5. **Scales** from personal use to public archive
6. **Aligns** with international standards

The key is to start simple (Dublin Core + basic poetry metadata) and evolve toward more sophisticated standards (TEI, Linked Data) as the project matures.

---

**Recommendation**: Implement metadata in phases, starting with Dublin Core core elements and poetry-specific fields, then gradually adding advanced features based on user needs and scholarly requirements.