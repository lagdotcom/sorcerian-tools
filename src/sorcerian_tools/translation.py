import tomllib
from pathlib import Path

loaded_generic_translations = False
generic_translations: dict[str, str] = {}


def get_generic_translations() -> dict[str, str]:
    global generic_translations, loaded_generic_translations
    if not loaded_generic_translations:
        with open(Path("translations") / "generic.toml", encoding="utf-8") as f:
            generic_translations = tomllib.loads(f.read())
            loaded_generic_translations = True

    return generic_translations
