"""
Language Mapper Utility for VPSWeb Repository System

This module provides mapping between BCP-47 language codes and natural language names,
with support for common translation languages used in poetry.

Features:
- BCP-47 to natural language name mapping
- Natural language to BCP-47 code mapping
- Language validation and normalization
- Support for regional variants and scripts
- Poetry-specific language metadata
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple


class LanguageDirection(str, Enum):
    """Text direction for languages."""

    LTR = "ltr"  # Left-to-right
    RTL = "rtl"  # Right-to-left


class ScriptType(str, Enum):
    """Writing script types."""

    LATIN = "latin"
    CYRILLIC = "cyrillic"
    ARABIC = "arabic"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    KOREAN = "korean"
    DEVANAGARI = "devanagari"
    GREEK = "greek"
    HEBREW = "hebrew"
    THAI = "thai"


class LanguageInfo:
    """
    Comprehensive language information for poetry translation.

    Contains metadata about languages commonly used in poetry,
    including script, direction, and poetic traditions.
    """

    def __init__(
        self,
        code: str,
        name: str,
        native_name: str,
        direction: LanguageDirection = LanguageDirection.LTR,
        script: ScriptType = ScriptType.LATIN,
        poetic_tradition: bool = True,
        common_in_translation: bool = True,
        regional_variants: Optional[List[str]] = None,
    ):
        self.code = code
        self.name = name
        self.native_name = native_name
        self.direction = direction
        self.script = script
        self.poetic_tradition = poetic_tradition
        self.common_in_translation = common_in_translation
        self.regional_variants = regional_variants or []

    def __repr__(self) -> str:
        return f"LanguageInfo(code='{self.code}', name='{self.name}')"


class LanguageMapper:
    """
    Maps BCP-47 language codes to natural language names and metadata.

    Provides bidirectional mapping between language codes and names,
    with validation and normalization capabilities.
    """

    def __init__(self):
        """Initialize the language mapper with predefined languages."""
        self._code_to_info: Dict[str, LanguageInfo] = {}
        self._name_to_code: Dict[str, str] = {}
        self._native_name_to_code: Dict[str, str] = {}

        self._initialize_languages()

    def _initialize_languages(self) -> None:
        """Initialize the language database with common poetry languages."""

        # Major languages with strong poetic traditions
        languages = [
            # English
            LanguageInfo(
                code="en",
                name="English",
                native_name="English",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=[
                    "en-US",
                    "en-GB",
                    "en-AU",
                    "en-CA",
                    "en-IE",
                ],
            ),
            # Chinese
            LanguageInfo(
                code="zh-CN",
                name="Chinese",
                native_name="中文",
                direction=LanguageDirection.LTR,
                script=ScriptType.CHINESE,
                regional_variants=["zh-CN", "zh-TW", "zh-HK", "zh-SG"],
            ),
            # Classical Chinese
            LanguageInfo(
                code="zh-Hant",
                name="Classical Chinese",
                native_name="文言文",
                direction=LanguageDirection.LTR,
                script=ScriptType.CHINESE,
                poetic_tradition=True,
            ),
            # Japanese
            LanguageInfo(
                code="ja",
                name="Japanese",
                native_name="日本語",
                direction=LanguageDirection.LTR,
                script=ScriptType.JAPANESE,
                regional_variants=["ja-JP"],
            ),
            # Korean
            LanguageInfo(
                code="ko",
                name="Korean",
                native_name="한국어",
                direction=LanguageDirection.LTR,
                script=ScriptType.KOREAN,
                regional_variants=["ko-KR"],
            ),
            # French
            LanguageInfo(
                code="fr",
                name="French",
                native_name="Français",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["fr-FR", "fr-CA", "fr-BE", "fr-CH"],
            ),
            # German
            LanguageInfo(
                code="de",
                name="German",
                native_name="Deutsch",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["de-DE", "de-AT", "de-CH"],
            ),
            # Spanish
            LanguageInfo(
                code="es",
                name="Spanish",
                native_name="Español",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["es-ES", "es-MX", "es-AR", "es-CO"],
            ),
            # Italian
            LanguageInfo(
                code="it",
                name="Italian",
                native_name="Italiano",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["it-IT", "it-CH"],
            ),
            # Portuguese
            LanguageInfo(
                code="pt",
                name="Portuguese",
                native_name="Português",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["pt-PT", "pt-BR"],
            ),
            # Russian
            LanguageInfo(
                code="ru",
                name="Russian",
                native_name="Русский",
                direction=LanguageDirection.LTR,
                script=ScriptType.CYRILLIC,
                regional_variants=["ru-RU"],
            ),
            # Arabic
            LanguageInfo(
                code="ar",
                name="Arabic",
                native_name="العربية",
                direction=LanguageDirection.RTL,
                script=ScriptType.ARABIC,
                regional_variants=["ar-SA", "ar-EG", "ar-MA", "ar-IQ"],
            ),
            # Hindi
            LanguageInfo(
                code="hi",
                name="Hindi",
                native_name="हिन्दी",
                direction=LanguageDirection.LTR,
                script=ScriptType.DEVANAGARI,
                regional_variants=["hi-IN"],
            ),
            # Sanskrit (Classical)
            LanguageInfo(
                code="sa",
                name="Sanskrit",
                native_name="संस्कृतम्",
                direction=LanguageDirection.LTR,
                script=ScriptType.DEVANAGARI,
                poetic_tradition=True,
            ),
            # Persian
            LanguageInfo(
                code="fa",
                name="Persian",
                native_name="فارسی",
                direction=LanguageDirection.RTL,
                script=ScriptType.ARABIC,
                regional_variants=["fa-IR", "fa-AF"],
            ),
            # Urdu
            LanguageInfo(
                code="ur",
                name="Urdu",
                native_name="اردو",
                direction=LanguageDirection.RTL,
                script=ScriptType.ARABIC,
                regional_variants=["ur-PK", "ur-IN"],
            ),
            # Turkish
            LanguageInfo(
                code="tr",
                name="Turkish",
                native_name="Türkçe",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["tr-TR"],
            ),
            # Greek
            LanguageInfo(
                code="el",
                name="Greek",
                native_name="Ελληνικά",
                direction=LanguageDirection.LTR,
                script=ScriptType.GREEK,
                regional_variants=["el-GR"],
            ),
            # Hebrew
            LanguageInfo(
                code="he",
                name="Hebrew",
                native_name="עברית",
                direction=LanguageDirection.RTL,
                script=ScriptType.HEBREW,
                regional_variants=["he-IL"],
            ),
            # Dutch
            LanguageInfo(
                code="nl",
                name="Dutch",
                native_name="Nederlands",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["nl-NL", "nl-BE"],
            ),
            # Swedish
            LanguageInfo(
                code="sv",
                name="Swedish",
                native_name="Svenska",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["sv-SE"],
            ),
            # Norwegian
            LanguageInfo(
                code="no",
                name="Norwegian",
                native_name="Norsk",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["nb-NO", "nn-NO"],
            ),
            # Danish
            LanguageInfo(
                code="da",
                name="Danish",
                native_name="Dansk",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["da-DK"],
            ),
            # Finnish
            LanguageInfo(
                code="fi",
                name="Finnish",
                native_name="Suomi",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["fi-FI"],
            ),
            # Polish
            LanguageInfo(
                code="pl",
                name="Polish",
                native_name="Polski",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["pl-PL"],
            ),
            # Czech
            LanguageInfo(
                code="cs",
                name="Czech",
                native_name="Čeština",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["cs-CZ"],
            ),
            # Hungarian
            LanguageInfo(
                code="hu",
                name="Hungarian",
                native_name="Magyar",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["hu-HU"],
            ),
            # Romanian
            LanguageInfo(
                code="ro",
                name="Romanian",
                native_name="Română",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["ro-RO"],
            ),
            # Ukrainian
            LanguageInfo(
                code="uk",
                name="Ukrainian",
                native_name="Українська",
                direction=LanguageDirection.LTR,
                script=ScriptType.CYRILLIC,
                regional_variants=["uk-UA"],
            ),
            # Bulgarian
            LanguageInfo(
                code="bg",
                name="Bulgarian",
                native_name="Български",
                direction=LanguageDirection.LTR,
                script=ScriptType.CYRILLIC,
                regional_variants=["bg-BG"],
            ),
            # Thai
            LanguageInfo(
                code="th",
                name="Thai",
                native_name="ไทย",
                direction=LanguageDirection.LTR,
                script=ScriptType.THAI,
                regional_variants=["th-TH"],
            ),
            # Vietnamese
            LanguageInfo(
                code="vi",
                name="Vietnamese",
                native_name="Tiếng Việt",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["vi-VN"],
            ),
            # Indonesian
            LanguageInfo(
                code="id",
                name="Indonesian",
                native_name="Bahasa Indonesia",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["id-ID"],
            ),
            # Malay
            LanguageInfo(
                code="ms",
                name="Malay",
                native_name="Bahasa Melayu",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                regional_variants=["ms-MY", "ms-SG"],
            ),
            # Latin (Classical)
            LanguageInfo(
                code="la",
                name="Latin",
                native_name="Latina",
                direction=LanguageDirection.LTR,
                script=ScriptType.LATIN,
                poetic_tradition=True,
            ),
            # Ancient Greek
            LanguageInfo(
                code="grc",
                name="Ancient Greek",
                native_name="Ἀρχαία ἑλληνικὴ",
                direction=LanguageDirection.LTR,
                script=ScriptType.GREEK,
                poetic_tradition=True,
            ),
        ]

        # Build lookup dictionaries
        for lang in languages:
            self._code_to_info[lang.code] = lang
            self._name_to_code[lang.name.lower()] = lang.code
            self._native_name_to_code[lang.native_name.lower()] = lang.code

            # Also add regional variants
            for variant in lang.regional_variants:
                self._code_to_info[variant] = lang

    def get_language_info(self, code: str) -> Optional[LanguageInfo]:
        """
        Get language information by BCP-47 code.

        Args:
            code: BCP-47 language code

        Returns:
            LanguageInfo object or None if not found
        """
        return self._code_to_info.get(self.normalize_code(code))

    def get_language_name(self, code: str) -> Optional[str]:
        """
        Get English language name by BCP-47 code.

        Args:
            code: BCP-47 language code

        Returns:
            Language name or None if not found
        """
        info = self.get_language_info(code)
        return info.name if info else None

    def get_native_language_name(self, code: str) -> Optional[str]:
        """
        Get native language name by BCP-47 code.

        Args:
            code: BCP-47 language code

        Returns:
            Native language name or None if not found
        """
        info = self.get_language_info(code)
        return info.native_name if info else None

    def get_language_code(self, name: str) -> Optional[str]:
        """
        Get BCP-47 language code by language name.

        Args:
            name: Language name (English or native)

        Returns:
            BCP-47 language code or None if not found
        """
        normalized_name = name.strip().lower()
        return self._name_to_code.get(normalized_name) or self._native_name_to_code.get(normalized_name)

    def normalize_code(self, code: str) -> str:
        """
        Normalize BCP-47 language code.

        Args:
            code: Raw language code

        Returns:
            Normalized language code
        """
        code = code.strip().lower()

        # Handle common variations
        if code in ["zh-cn", "zh hans"]:
            return "zh-CN"
        elif code in ["zh-tw", "zh hant"]:
            return "zh-TW"
        elif code in ["en-us"]:
            return "en-US"
        elif code in ["en-gb"]:
            return "en-GB"

        return code

    def is_valid_language_code(self, code: str) -> bool:
        """
        Check if a BCP-47 language code is valid and supported.

        Args:
            code: BCP-47 language code

        Returns:
            True if valid and supported
        """
        return self.get_language_info(code) is not None

    def is_valid_language_name(self, name: str) -> bool:
        """
        Check if a language name is valid and supported.

        Args:
            name: Language name (English or native)

        Returns:
            True if valid and supported
        """
        return self.get_language_code(name) is not None

    def get_poetry_languages(self) -> List[LanguageInfo]:
        """
        Get all languages with strong poetic traditions.

        Returns:
            List of LanguageInfo objects for poetry languages
        """
        return [info for info in self._code_to_info.values() if info.poetic_tradition]

    def get_common_translation_languages(self) -> List[LanguageInfo]:
        """
        Get languages commonly used in translation.

        Returns:
            List of LanguageInfo objects for common translation languages
        """
        return [info for info in self._code_to_info.values() if info.common_in_translation]

    def get_rtl_languages(self) -> List[LanguageInfo]:
        """
        Get all right-to-left languages.

        Returns:
            List of LanguageInfo objects for RTL languages
        """
        return [info for info in self._code_to_info.values() if info.direction == LanguageDirection.RTL]

    def get_languages_by_script(self, script: ScriptType) -> List[LanguageInfo]:
        """
        Get languages by writing script.

        Args:
            script: Script type to filter by

        Returns:
            List of LanguageInfo objects for the specified script
        """
        return [info for info in self._code_to_info.values() if info.script == script]

    def search_languages(self, query: str) -> List[LanguageInfo]:
        """
        Search languages by name or code.

        Args:
            query: Search query

        Returns:
            List of matching LanguageInfo objects
        """
        query = query.strip().lower()
        results = []

        for code, info in self._code_to_info.items():
            if query in code.lower() or query in info.name.lower() or query in info.native_name.lower():
                results.append(info)

        return results

    def get_all_languages(self) -> Dict[str, LanguageInfo]:
        """
        Get all supported languages.

        Returns:
            Dictionary mapping language codes to LanguageInfo objects
        """
        return dict(self._code_to_info)

    def add_custom_language(self, info: LanguageInfo) -> None:
        """
        Add a custom language to the mapper.

        Args:
            info: LanguageInfo object for the custom language
        """
        self._code_to_info[info.code] = info
        self._name_to_code[info.name.lower()] = info.code
        self._native_name_to_code[info.native_name.lower()] = info.code


# Global language mapper instance
_language_mapper: Optional[LanguageMapper] = None


def get_language_mapper() -> LanguageMapper:
    """
    Get the global language mapper instance.

    Returns:
        Global LanguageMapper instance
    """
    global _language_mapper
    if _language_mapper is None:
        _language_mapper = LanguageMapper()
    return _language_mapper


def validate_language_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a BCP-47 language code.

    Args:
        code: Language code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code or not code.strip():
        return False, "Language code cannot be empty"

    code = code.strip()

    # Basic BCP-47 format validation
    if not re.match(r"^[a-z]{2}(-[A-Z][a-z]{3})?(-[A-Z]{2})?(-[A-Z0-9]{5,8})?$", code):
        return False, f"Invalid BCP-47 language code format: {code}"

    mapper = get_language_mapper()
    if not mapper.is_valid_language_code(code):
        return False, f"Language code not supported: {code}"

    return True, None


def get_display_name(code: str, use_native: bool = False) -> str:
    """
    Get display name for a language code.

    Args:
        code: BCP-47 language code
        use_native: Whether to use native name instead of English

    Returns:
        Display name for the language
    """
    mapper = get_language_mapper()

    if use_native:
        return mapper.get_native_language_name(code) or code
    else:
        return mapper.get_language_name(code) or code


# Common language pairs for poetry translation
COMMON_TRANSLATION_PAIRS = [
    ("en", "zh-CN"),  # English ↔ Chinese
    ("zh-CN", "en"),  # Chinese ↔ English
    ("en", "ja"),  # English ↔ Japanese
    ("ja", "en"),  # Japanese ↔ English
    ("en", "fr"),  # English ↔ French
    ("fr", "en"),  # French ↔ English
    ("en", "de"),  # English ↔ German
    ("de", "en"),  # German ↔ English
    ("en", "es"),  # English ↔ Spanish
    ("es", "en"),  # Spanish ↔ English
    ("en", "ru"),  # English ↔ Russian
    ("ru", "en"),  # Russian ↔ English
    ("en", "ar"),  # English ↔ Arabic
    ("ar", "en"),  # Arabic ↔ English
    ("zh-CN", "ja"),  # Chinese ↔ Japanese
    ("ja", "zh-CN"),  # Japanese ↔ Chinese
    ("fr", "de"),  # French ↔ German
    ("de", "fr"),  # German ↔ French
    ("es", "fr"),  # Spanish ↔ French
    ("fr", "es"),  # French ↔ Spanish
]


def get_common_translation_pairs() -> List[Tuple[str, str]]:
    """
    Get common language pairs for poetry translation.

    Returns:
        List of (source_code, target_code) tuples
    """
    return COMMON_TRANSLATION_PAIRS.copy()
