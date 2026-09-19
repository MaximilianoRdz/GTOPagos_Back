"""
Skill: SmartCategorizerSkill
Categorización semántica y heurística de descripciones y conceptos financieros.
"""
import re
from decimal import Decimal
from agent.specs.schemas import CategorizerInput, CategorizerOutput

KEYWORD_RULES = {
    "Servicios del Hogar": {
        "behavior": "EXPENSE",
        "keywords": ["cfe", "luz", "agua", "internet", "telmex", "izzi", "totalplay", "gas", "infonavit"]
    },
    "Entretenimiento & Suscripciones": {
        "behavior": "EXPENSE",
        "keywords": ["netflix", "spotify", "hbo", "disney", "prime", "youtube", "steam", "playstation", "cine", "nintendo"]
    },
    "Transporte & Combustible": {
        "behavior": "EXPENSE",
        "keywords": ["gasolina", "pemex", "oxxo gas", "bp", "shell", "uber", "didi", "metro", "caseta", "estacionamiento"]
    },
    "Alimentos & Supermercado": {
        "behavior": "EXPENSE",
        "keywords": ["walmart", "soriana", "heb", "chedraui", "aurrera", "costco", "sams", "super", "despensa", "oxxo"]
    },
    "Comida Fuera & Restaurantes": {
        "behavior": "EXPENSE",
        "keywords": ["restaurante", "tacos", "pizza", "burger", "starbucks", "rappi", "uber eats", "didi food", "cafeteria"]
    },
    "Salud & Farmacia": {
        "behavior": "EXPENSE",
        "keywords": ["farmacia", "guadalajara", "ahorro", "san pablo", "simi", "doctor", "consulta", "medico", "laboratorio"]
    },
    "Sueldos & Salarios": {
        "behavior": "INCOME",
        "keywords": ["nomina", "sueldo", "salario", "quincena", "honorarios", "aguinaldo", "deposito recibido"]
    },
    "Ventas & Negocios": {
        "behavior": "INCOME",
        "keywords": ["pago cliente", "transferencia recibida", "venta", "comision", "cobro"]
    }
}


def categorize_expense(payload: CategorizerInput) -> CategorizerOutput:
    clean_text = payload.description.lower().strip()
    words = re.findall(r'\b\w+\b', clean_text)

    best_category = "Varios / Otros"
    best_behavior = "EXPENSE"
    highest_confidence = Decimal('0.30')
    matched_word = None

    for category, config in KEYWORD_RULES.items():
        for kw in config["keywords"]:
            # Coincidencia exacta de frase
            if kw in clean_text:
                confidence = Decimal('0.95') if kw in words else Decimal('0.85')
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_category = category
                    best_behavior = config["behavior"]
                    matched_word = kw
                    break

    return CategorizerOutput(
        original_text=payload.description,
        suggested_category=best_category,
        behavior=best_behavior,
        confidence=highest_confidence,
        matched_keyword=matched_word
    )
