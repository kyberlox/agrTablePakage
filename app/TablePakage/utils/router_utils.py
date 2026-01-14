import re
from transliterate import translit


def to_sql_name_lat(name: str) -> str:
    # Замена кириллицы на латиницу транслитом
    name = name.lower()
    name = translit(name, "ru", reversed=True)
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def to_sql_name_kir(name: str) -> str:
    # Замена латиницы на кириллицу транслитом
    name = name.lower()
    name = translit(name, "ru")
    name = re.sub(r"_", " ", name)
    return name.strip("_")
