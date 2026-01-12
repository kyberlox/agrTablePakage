from transliterate import translit


def to_sql_name_lat(name: str) -> str:
    # Замена кириллицы на латиницу транслитом
    return translit(name.lower(), 'ru', reversed=True).replace(" ", "_")


def to_sql_name_kir(name: str) -> str:
    # Замена латиницы на кириллицу транслитом
    return translit(name.lower(), 'ru').replace("_", " ")
