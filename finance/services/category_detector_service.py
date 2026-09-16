from finance.models import CategoryKeyword, Category


def detect_category_from_description(description: str) -> tuple[Category | None, float]:
    """
    Detecta la categoría correspondiente a una descripción de transacción
    analizando palabras clave ordenadas por especificidad.
    Retorna una tupla (categoría, nivel_de_confianza).
    """
    if not description or not description.strip():
        return None, 0.0

    description_lower = description.lower()

    # Priorizar coincidencias más específicas primero (ej. "telcel plan" antes de "telcel")
    keywords = CategoryKeyword.objects.select_related('category').all()
    sorted_keywords = sorted(keywords, key=lambda x: len(x.keyword), reverse=True)

    for kw in sorted_keywords:
        if kw.keyword in description_lower:
            return kw.category, 0.95

    return None, 0.0
