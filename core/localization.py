from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


DEFAULT_LANGUAGE = "ko"
FALLBACK_LANGUAGE = "en"


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    code: str
    name: str


class LocalizationManager:
    def __init__(self) -> None:
        self._language = DEFAULT_LANGUAGE
        self._locales_dir: Path | None = None
        self._strings: dict[str, str] = {}
        self._fallback: dict[str, str] = {}

    @property
    def language(self) -> str:
        return self._language

    def configure(self, locales_dir: Path, language: str) -> None:
        self._locales_dir = locales_dir
        self._fallback = self._load_strings(FALLBACK_LANGUAGE)
        self._language = self._normalize_language(language)
        self._strings = self._load_strings(self._language)

    def available_languages(self, locales_dir: Path | None = None) -> list[LanguageInfo]:
        directory = locales_dir or self._locales_dir
        if directory is None or not directory.exists():
            return [LanguageInfo(DEFAULT_LANGUAGE, "한국어"), LanguageInfo(FALLBACK_LANGUAGE, "English")]
        languages: list[LanguageInfo] = []
        for path in sorted(directory.glob("*.ini")):
            code = path.stem
            parser = self._read_parser(path)
            name = parser.get("meta", "name", fallback=code)
            languages.append(LanguageInfo(code, name))
        return languages

    def text(self, key: str, **kwargs: object) -> str:
        template = self._strings.get(key, self._fallback.get(key, key))
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, ValueError):
                return template
        return template

    def _normalize_language(self, language: str) -> str:
        code = (language or DEFAULT_LANGUAGE).strip().lower()
        if self._locales_dir is not None and not (self._locales_dir / f"{code}.ini").exists():
            return DEFAULT_LANGUAGE
        return code

    def _load_strings(self, language: str) -> dict[str, str]:
        if self._locales_dir is None:
            return {}
        path = self._locales_dir / f"{language}.ini"
        if not path.exists():
            return {}
        parser = self._read_parser(path)
        if not parser.has_section("strings"):
            return {}
        return {key: value for key, value in parser.items("strings")}

    @staticmethod
    def _read_parser(path: Path) -> ConfigParser:
        parser = ConfigParser()
        parser.optionxform = str
        parser.read(path, encoding="utf-8")
        return parser


_manager = LocalizationManager()


def configure_localization(locales_dir: Path, language: str) -> None:
    _manager.configure(locales_dir, language)


def available_languages(locales_dir: Path) -> list[LanguageInfo]:
    return _manager.available_languages(locales_dir)


def tr(key: str, **kwargs: object) -> str:
    return _manager.text(key, **kwargs)
