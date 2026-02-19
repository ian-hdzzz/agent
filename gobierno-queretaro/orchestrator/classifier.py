"""
Gobierno Queretaro - Intent Classifier
Dynamic category classification for routing to specialized agents.

Classifier data is built dynamically from the agent registry DB when available,
falling back to static constants when the DB is unreachable.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from anthropic import Anthropic
from pydantic import BaseModel, Field

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Directory for externalized prompts (hot-reloadable without redeployment)
PROMPTS_DIR = Path(__file__).parent / "prompts"


# ============================================
# Category Definitions (kept for backward compat imports)
# ============================================

CategoryCode = Literal[
    "CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL",
    "RPP", "LAB", "VIV", "APP", "SOC", "ATC", "EXIT",
]


# ============================================
# Static fallback data (used when DB unavailable)
# ============================================

_STATIC_KEYWORD_MAP: dict[str, list[str]] = {
    "ATC": [
        "atencion ciudadana", "contactanos", "4421015205",
        "queja general", "sugerencia general", "informacion general",
    ],
    "CEA": [
        "agua", "fuga", "fugas", "deuda de agua", "consumo de agua",
        "recibo de agua", "medidor", "alcantarillado", "drenaje",
        "reconexion", "corte de agua", "no hay agua", "agua turbia",
        "cea", "saldo de agua", "aclaracion agua", "contrato agua",
        "lectura medidor", "recibo digital agua",
    ],
    "TRA": [
        "autobus", "autobus", "camion", "camion", "ruta", "transporte",
        "parada", "horario de camion", "tarjeta de transporte", "ameq",
        "transporte publico", "qrobus", "qro bus",
        "tarjeta preferente", "tarjeta estudiante", "credencial estudiante",
        "adulto mayor transporte", "inapam transporte", "tercera edad transporte",
        "persona con discapacidad transporte", "discapacidad transporte",
        "nino 3 a 6", "nino 3 a 6",
        "tarifa unidos", "tarifa $2", "tarifa 2 pesos",
        "tarjeta prepago", "saldo tarjeta transporte", "historial tarjeta",
        "recargar tarjeta", "recarga qrobus",
        "como llego", "que ruta", "punto a punto",
        "mapa ruta", "descargar mapa ruta",
        "permiso transporte", "concesion transporte", "tio transporte",
        "tramites vehiculo transporte",
        "evaluar transporte", "sugerir transporte", "iqt", "iqtapp",
    ],
    "EDU": [
        "escuela", "inscripcion", "inscripcion", "preinscripcion",
        "educacion", "educacion", "usebeq", "colegio",
        "preparatoria", "secundaria", "primaria",
        "vinculacion parental", "vinculacion", "verifica vinculacion",
        "curp aspirante", "preasignacion", "said",
        "asesoria educativa", "ciclo escolar",
    ],
    "VEH": [
        "placa", "placas", "multa", "multas", "licencia de conducir",
        "registro vehicular", "tenencia", "verificacion", "verificacion",
        "carro", "vehiculo", "vehiculo", "auto", "motocicleta",
        "pago tenencia", "tenencia 2026", "tenencia 2025",
        "oficina recaudadora", "consulta pago vehiculo",
        "comprobante pago vehiculo", "descarga comprobante",
        "preguntas frecuentes tenencia",
        "sustitucion placa", "placa perdida", "placa lluvia", "placa desgastada",
        "reposicion placa", "portal tributario",
    ],
    "PSI": [
        "psicologo", "psicologo", "psicologia", "psicologia",
        "salud mental", "ansiedad", "depresion", "depresion",
        "terapia", "sejuve", "orientacion juvenil", "cita psicologica",
        "ser tranquilidad", "primeros auxilios emocionales",
        "atencion psicologica", "apoyo emocional",
    ],
    "IQM": [
        "violencia", "mujer", "mujeres", "genero", "genero", "acoso",
        "maltrato", "iqm", "atencion a mujeres", "asesoria legal mujer",
        "refugio", "violencia domestica", "violencia familiar",
        "tel mujer", "4422164757", "instituto queretano de la mujer",
        "centros atencion mujer", "pasos ante violencia",
        "asesoria legal iqm", "asesoria psicologica iqm",
    ],
    "CUL": [
        "cultura", "museo", "museos", "teatro", "taller cultural", "evento",
        "concierto", "exposicion", "biblioteca", "arte", "beca cultural",
        "danza", "musica", "pintura",
        "centro cultural", "galeria libertad", "galeria libertad",
        "arte emergente", "centro artes queretaro",
        "casa del faldon", "casa faldon", "centro queretano imagen",
        "museo arte contemporaneo", "museo arte queretaro",
        "museo ciudad", "museo conspiradores", "museo restauracion",
        "museo anbanica", "museo sierra gorda", "museo pinal amoles",
        "secretaria cultura", "cartelera cultural",
        "la cultura esta en nosotros",
    ],
    "RPP": [
        "registro publico", "rpp", "propiedad", "inmueble",
        "consulta inmobiliaria", "cerlin", "clave catastral", "folio inmueble",
        "certificado gravamen", "libertad gravamen",
        "certificado inscripcion", "certificado propiedad",
        "unica propiedad", "no propiedad", "historial registral",
        "busqueda antecedentes", "copias certificadas",
        "cancelacion hipoteca", "infonavit cancelar", "fovissste cancelar",
        "cancelacion caducidad", "demanda embargo", "inscripcion judicial",
        "validacion testamento", "validez testamento",
        "nombramiento albacea", "herencia",
        "alerta registral", "seguimiento tramite rpp",
        "horario rpp", "ubicacion rpp", "costos rpp",
        "aclaraciones rpp", "rechazo certificado",
    ],
    "LAB": [
        "trabajo", "despido", "demanda laboral", "conciliacion laboral",
        "conciliacion laboral", "derechos laborales", "finiquito",
        "liquidacion", "liquidacion", "cclq", "junta de conciliacion",
        "asesoria juridica laboral", "proceso conciliacion",
        "convenio laboral", "ratificacion convenio",
        "asunto colectivo", "sindicato",
        "procuraduria defensa trabajo",
        "asunto anterior noviembre 2021", "asunto anterior 2021",
    ],
    "VIV": [
        "vivienda", "casa", "credito hipotecario", "credito hipotecario",
        "iveq", "programa de vivienda", "terreno", "lote",
        "escrituras", "subsidio vivienda",
        "constancia no adeudo vivienda", "expedicion planos",
        "cesion derechos", "emision instruccion notarial",
        "autoproduccion", "autoproduccion municipios",
        "vivienda trabajadores estado",
        "juntos por tu vivienda", "escriturar iveq",
        "regularizacion vivienda", "cita iveq",
    ],
    "APP": [
        "app", "aplicacion", "aplicacion", "appqro", "error en app",
        "no funciona la app", "actualizar app", "descargar app",
        "problema con la aplicacion",
        "informacion appqro", "ayuda appqro",
        "contactar agente app",
    ],
    "SOC": [
        "programa social", "apoyo economico", "apoyo economico",
        "beneficio", "sedesoq", "despensa", "beca social",
        "tarjeta contigo", "problemas tarjeta contigo",
    ],
    "EXIT": [
        "gracias", "adios", "adios", "hasta luego", "bye", "chao",
        "ya no", "eso es todo", "nada mas", "nada mas",
    ],
}

_STATIC_CLASSIFICATION_PROMPT = """Eres el clasificador de intenciones del Portal de Gobierno de Queretaro.
Tu trabajo es categorizar cada mensaje del ciudadano en UNA de estas 13 categorias:

1. CEA - Agua CEA: agua, fugas, deuda de agua, consumos, reconexion, medidor, alcantarillado
2. TRA - Transporte AMEQ: rutas de autobus, horarios, tarjetas de transporte, paradas
3. EDU - Educacion USEBEQ: escuelas, inscripciones, becas educativas, constancias escolares
4. VEH - Vehiculos: placas, multas de transito, licencias de conducir, registro vehicular
5. PSI - Psicologia SEJUVE: citas psicologicas, salud mental, orientacion juvenil
6. IQM - Atencion a Mujeres: apoyo a mujeres, violencia de genero, orientacion legal
7. CUL - Cultura: eventos culturales, talleres, becas artisticas, museos, bibliotecas
8. RPP - Registro Publico: documentos oficiales, certificados, actas de nacimiento
9. LAB - Conciliacion Laboral: demandas laborales, despidos, derechos del trabajador
10. VIV - Vivienda IVEQ: creditos de vivienda, programas habitacionales
11. APP - APPQRO: soporte tecnico de la aplicacion movil del gobierno
12. SOC - Programas Sociales: beneficios sociales, ayudas economicas, apoyos
13. ATC - Atencion Ciudadana: quejas generales, sugerencias, PQRS que no encajan en otro
14. EXIT - El usuario quiere terminar la conversacion ("gracias", "adios", "ya no")

REGLAS IMPORTANTES:
- Si mencionan agua, fugas, recibos de agua, consumo de agua -> CEA
- Si mencionan camion, autobus, ruta, transporte publico -> TRA
- Si mencionan escuela, inscripcion, beca educativa -> EDU
- Si mencionan carro, placas, multa, licencia -> VEH
- Si mencionan psicologo, ansiedad, depresion, apoyo emocional -> PSI
- Si mencionan violencia, mujer, genero, acoso -> IQM
- Si mencionan museo, teatro, taller cultural, evento -> CUL
- Si mencionan acta, certificado, documento oficial -> RPP
- Si mencionan trabajo, despido, demanda laboral -> LAB
- Si mencionan casa, vivienda, credito hipotecario -> VIV
- Si mencionan app, aplicacion, error en app -> APP
- Si mencionan apoyo economico, programa social, ayuda -> SOC
- Si es una queja general o no encaja en ninguna categoria -> ATC
- Si el usuario se despide o agradece sin otra consulta -> EXIT

Responde SOLO con el codigo de categoria (CEA, TRA, EDU, VEH, PSI, IQM, CUL, RPP, LAB, VIV, APP, SOC, ATC, EXIT).
No incluyas explicaciones ni texto adicional."""

_STATIC_STRUCTURED_CLASSIFICATION_PROMPT = """Eres el clasificador de intenciones del Portal de Gobierno de Queretaro.
Analiza el mensaje del ciudadano y responde en formato JSON con la siguiente estructura:

{
    "category": "CEA|TRA|EDU|VEH|PSI|IQM|CUL|RPP|LAB|VIV|APP|SOC|ATC|EXIT",
    "confidence": 0.0-1.0,
    "entities": {
        "contract_number": "numero de contrato si se menciona",
        "location": "ubicacion mencionada",
        "date": "fecha mencionada",
        "person_name": "nombre de persona mencionado",
        "phone": "telefono mencionado"
    },
    "ambiguous": true/false,
    "clarification": "pregunta de clarificacion si es ambiguo",
    "urgency": "normal|high|emergency"
}

CATEGORIAS:
1. CEA - Agua: agua, fugas, deuda de agua, consumos, medidor
2. TRA - Transporte: rutas de autobus, horarios, tarjetas
3. EDU - Educacion: escuelas, inscripciones, becas educativas
4. VEH - Vehiculos: placas, multas, licencias
5. PSI - Psicologia: citas psicologicas, salud mental
6. IQM - Mujeres: violencia de genero, apoyo a mujeres
7. CUL - Cultura: eventos, talleres, museos
8. RPP - Registro: documentos, certificados, actas
9. LAB - Laboral: demandas, despidos, derechos laborales
10. VIV - Vivienda: creditos, programas habitacionales
11. APP - APPQRO: soporte tecnico de la app
12. SOC - Social: programas sociales, ayudas economicas
13. ATC - Atencion: quejas generales, otros
14. EXIT - Salir: despedidas, agradecimientos finales

REGLAS DE URGENCIA:
- "emergency": violencia activa, amenaza de vida, crisis
- "high": problemas urgentes de servicios, plazos cercanos
- "normal": consultas regulares

Responde SOLO con JSON valido, sin texto adicional."""

_STATIC_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "CEA": "Servicios de Agua (CEA)",
    "TRA": "Transporte Publico (AMEQ)",
    "EDU": "Educacion (USEBEQ)",
    "VEH": "Tramites Vehiculares",
    "PSI": "Psicologia (SEJUVE)",
    "IQM": "Atencion a Mujeres (IQM)",
    "CUL": "Cultura",
    "RPP": "Registro Publico (RPP)",
    "LAB": "Conciliacion Laboral (CCLQ)",
    "VIV": "Vivienda (IVEQ)",
    "APP": "Soporte APPQRO",
    "SOC": "Programas Sociales (SEDESOQ)",
    "ATC": "Atencion Ciudadana",
    "EXIT": "Fin de conversacion",
}

_STATIC_VALID_CATEGORIES: list[str] = [
    "CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL",
    "RPP", "LAB", "VIV", "APP", "SOC", "ATC", "EXIT",
]


# ============================================
# Dynamic Classifier Data
# ============================================

@dataclass
class DynamicClassifierData:
    """
    Classifier configuration built dynamically from the agent registry.

    Contains keyword maps, LLM prompts, and valid categories derived
    from whatever agents are currently registered and active.
    """

    keyword_map: dict[str, list[str]] = field(default_factory=dict)
    valid_categories: list[str] = field(default_factory=list)
    category_descriptions: dict[str, str] = field(default_factory=dict)
    classification_prompt: str = ""
    structured_classification_prompt: str = ""

    @classmethod
    def build_from_registry(cls, registry: dict[str, dict[str, Any]]) -> "DynamicClassifierData":
        """
        Build classifier data from the agent registry.

        Args:
            registry: Dict of category_code -> agent info (from AgentRegistry).
                      Each agent's info may contain a 'capabilities' dict with
                      'keywords', 'classification_hint', and 'category_description'.

        Returns:
            Fully populated DynamicClassifierData ready for use by classifier functions.
        """
        keyword_map: dict[str, list[str]] = {}
        valid_categories: list[str] = []
        category_descriptions: dict[str, str] = {}
        classification_lines: list[str] = []
        structured_lines: list[str] = []

        idx = 1
        for category_code, agent_info in sorted(registry.items()):
            valid_categories.append(category_code)

            caps = agent_info.get("capabilities", {})

            # Keywords
            keywords = caps.get("keywords", [])
            if keywords:
                keyword_map[category_code] = keywords

            # Category description
            cat_desc = caps.get("category_description", "")
            if cat_desc:
                category_descriptions[category_code] = cat_desc
            else:
                # Fall back to agent description
                category_descriptions[category_code] = agent_info.get("description", category_code)

            # Classification hint for LLM prompt
            hint = caps.get("classification_hint", "")
            if hint:
                classification_lines.append(f"{idx}. {category_code} - {cat_desc or category_code}: {hint}")
                structured_lines.append(f"{idx}. {category_code} - {cat_desc or category_code}: {hint}")
            else:
                desc = cat_desc or agent_info.get("description", category_code)
                classification_lines.append(f"{idx}. {category_code} - {desc}")
                structured_lines.append(f"{idx}. {category_code} - {desc}")

            idx += 1

        # Always append EXIT as a pseudo-category
        if "EXIT" not in valid_categories:
            valid_categories.append("EXIT")
            category_descriptions["EXIT"] = "Fin de conversacion"
            classification_lines.append(
                f"{idx}. EXIT - El usuario quiere terminar la conversacion (\"gracias\", \"adios\", \"ya no\")"
            )
            structured_lines.append(
                f"{idx}. EXIT - Salir: despedidas, agradecimientos finales"
            )
            # EXIT keywords
            keyword_map.setdefault("EXIT", [
                "gracias", "adios", "hasta luego", "bye", "chao",
                "ya no", "eso es todo", "nada mas",
            ])

        cat_count = len(valid_categories) - 1  # Exclude EXIT for count display
        codes_str = ", ".join(valid_categories)

        # Build classification prompt
        classification_prompt = (
            f"Eres el clasificador de intenciones del Portal de Gobierno de Queretaro.\n"
            f"Tu trabajo es categorizar cada mensaje del ciudadano en UNA de estas {cat_count} categorias:\n\n"
            + "\n".join(classification_lines)
            + "\n\nRESPONDE SOLO con el codigo de categoria ("
            + codes_str
            + ").\nNo incluyas explicaciones ni texto adicional."
        )

        # Build structured prompt
        structured_classification_prompt = (
            "Eres el clasificador de intenciones del Portal de Gobierno de Queretaro.\n"
            "Analiza el mensaje del ciudadano y responde en formato JSON con la siguiente estructura:\n\n"
            "{\n"
            '    "category": "' + "|".join(valid_categories) + '",\n'
            '    "confidence": 0.0-1.0,\n'
            '    "entities": {\n'
            '        "contract_number": "numero de contrato si se menciona",\n'
            '        "location": "ubicacion mencionada",\n'
            '        "date": "fecha mencionada",\n'
            '        "person_name": "nombre de persona mencionado",\n'
            '        "phone": "telefono mencionado"\n'
            "    },\n"
            '    "ambiguous": true/false,\n'
            '    "clarification": "pregunta de clarificacion si es ambiguo",\n'
            '    "urgency": "normal|high|emergency"\n'
            "}\n\n"
            "CATEGORIAS:\n"
            + "\n".join(structured_lines)
            + "\n\n"
            "REGLAS DE URGENCIA:\n"
            '- "emergency": violencia activa, amenaza de vida, crisis\n'
            '- "high": problemas urgentes de servicios, plazos cercanos\n'
            '- "normal": consultas regulares\n\n'
            "Responde SOLO con JSON valido, sin texto adicional."
        )

        return cls(
            keyword_map=keyword_map,
            valid_categories=valid_categories,
            category_descriptions=category_descriptions,
            classification_prompt=classification_prompt,
            structured_classification_prompt=structured_classification_prompt,
        )


def _get_classifier_data() -> DynamicClassifierData:
    """
    Get classifier data, preferring dynamic data from DB registry.

    Falls back to static constants when the registry has no classifier data
    (e.g. DB unavailable or agents haven't registered keywords yet).
    """
    from .config import _get_registry_instance

    registry_instance = _get_registry_instance()
    data = registry_instance.get_classifier_data()
    if data is not None:
        return data

    # Static fallback
    return DynamicClassifierData(
        keyword_map=_STATIC_KEYWORD_MAP,
        valid_categories=_STATIC_VALID_CATEGORIES,
        category_descriptions=_STATIC_CATEGORY_DESCRIPTIONS,
        classification_prompt=_STATIC_CLASSIFICATION_PROMPT,
        structured_classification_prompt=_STATIC_STRUCTURED_CLASSIFICATION_PROMPT,
    )


class StructuredClassification(BaseModel):
    """Structured classification result with entity extraction."""

    category: str = Field(description="Category code")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    entities: dict[str, str | None] = Field(
        default_factory=dict,
        description="Extracted entities from message",
    )
    ambiguous: bool = Field(default=False, description="Whether classification is ambiguous")
    clarification: str | None = Field(
        default=None,
        description="Clarification question if ambiguous",
    )
    urgency: str = Field(default="normal", description="Message urgency level")
    method: str = Field(default="llm_structured", description="Classification method")
    raw_response: str | None = Field(default=None, description="Raw LLM response")


# ============================================
# Keyword-based Pre-classification
# ============================================

def keyword_classify(message: str) -> str | None:
    """
    Fast keyword-based classification.

    Returns category code if confident match found,
    None if LLM classification is needed.
    """
    data = _get_classifier_data()
    lower_message = message.lower()

    # Check each category's keywords
    matches: dict[str, int] = {}

    for category, keywords in data.keyword_map.items():
        score = sum(1 for kw in keywords if kw in lower_message)
        if score > 0:
            matches[category] = score

    if not matches:
        return None

    # Return highest scoring category if clear winner
    sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_matches) == 1:
        return sorted_matches[0][0]

    # If top two are close, let LLM decide
    if sorted_matches[0][1] > sorted_matches[1][1] * 2:
        return sorted_matches[0][0]

    return None


# ============================================
# Prompt Loading
# ============================================

def load_classification_prompt() -> str:
    """
    Load the classification prompt.

    Priority:
    1. Dynamic prompt from registry (if agents have classification_hint)
    2. External file (hot-reloadable)
    3. Static fallback constant
    """
    # Try dynamic first
    data = _get_classifier_data()
    if data.classification_prompt and data.classification_prompt != _STATIC_CLASSIFICATION_PROMPT:
        return data.classification_prompt

    # Try external file
    prompt_file = PROMPTS_DIR / "classification_prompt.txt"
    try:
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to load prompt from {prompt_file}: {e}")

    return data.classification_prompt


# ============================================
# LLM Classification
# ============================================

async def llm_classify(message: str, context: str | None = None) -> dict[str, Any]:
    """
    Classify message using Claude LLM.

    Args:
        message: User message to classify
        context: Additional context (conversation history)

    Returns:
        Classification result with category and confidence
    """
    data = _get_classifier_data()
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = load_classification_prompt()
    if context:
        prompt = f"Historial de conversacion:\n{context}\n\n{prompt}"

    try:
        response = client.messages.create(
            model=settings.model,
            max_tokens=10,
            temperature=settings.classification_temperature,
            system=prompt,
            messages=[{"role": "user", "content": message}],
        )

        # Extract category from response
        content = response.content[0].text.strip().upper()

        category = "ATC"  # Default
        for cat in data.valid_categories:
            if cat in content:
                category = cat
                break

        logger.info(f"LLM classified '{message[:50]}...' as {category}")

        return {
            "category": category,
            "raw_response": content,
            "confidence": 0.9 if category != "ATC" else 0.5,
            "method": "llm",
        }

    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        return {
            "category": "ATC",
            "error": str(e),
            "confidence": 0.3,
            "method": "fallback",
        }


# ============================================
# Main Classifier
# ============================================

async def classify_intent(
    message: str,
    context: str | None = None,
    use_keywords: bool = True,
) -> dict[str, Any]:
    """
    Classify user intent using keyword matching first, then LLM.

    Args:
        message: User message
        context: Conversation context (optional)
        use_keywords: Whether to try keyword matching first

    Returns:
        Classification result with category and confidence
    """
    # Try keyword classification first
    if use_keywords:
        keyword_result = keyword_classify(message)
        if keyword_result:
            logger.info(f"Keyword classified '{message[:50]}...' as {keyword_result}")
            return {
                "category": keyword_result,
                "confidence": 0.85,
                "method": "keyword",
            }

    # Fall back to LLM
    return await llm_classify(message, context)


# ============================================
# Structured LLM Classification
# ============================================

async def llm_classify_structured(
    message: str,
    context: str | None = None,
) -> StructuredClassification:
    """
    Enhanced classification with entity extraction and ambiguity detection.

    Returns structured JSON with:
    - category and confidence
    - extracted entities (contract_number, location, date, etc.)
    - ambiguity flag and clarification question
    - urgency level
    """
    data = _get_classifier_data()
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = data.structured_classification_prompt
    if context:
        prompt = f"Historial de conversacion:\n{context}\n\n{prompt}"

    try:
        response = client.messages.create(
            model=settings.model,
            max_tokens=500,
            temperature=settings.classification_temperature,
            system=prompt,
            messages=[{"role": "user", "content": message}],
        )

        # Extract and parse JSON response
        content = response.content[0].text.strip()

        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")

        # Validate category against dynamic valid_categories
        category = parsed.get("category", "ATC").upper()
        if category not in data.valid_categories:
            category = "ATC"

        logger.info(
            f"Structured LLM classified '{message[:50]}...' as {category} "
            f"(confidence={parsed.get('confidence', 0):.2f}, "
            f"ambiguous={parsed.get('ambiguous', False)})"
        )

        return StructuredClassification(
            category=category,
            confidence=float(parsed.get("confidence", 0.8)),
            entities=parsed.get("entities", {}),
            ambiguous=bool(parsed.get("ambiguous", False)),
            clarification=parsed.get("clarification"),
            urgency=parsed.get("urgency", "normal"),
            method="llm_structured",
            raw_response=content,
        )

    except Exception as e:
        logger.error(f"Structured LLM classification error: {e}")
        return StructuredClassification(
            category="ATC",
            confidence=0.3,
            entities={},
            ambiguous=True,
            clarification="No pude entender tu solicitud. Podrias ser mas especifico?",
            urgency="normal",
            method="fallback",
            raw_response=str(e),
        )


async def classify_intent_structured(
    message: str,
    context: str | None = None,
    use_keywords: bool = True,
) -> StructuredClassification:
    """
    Enhanced classify with full structured output.

    Combines keyword pre-classification with structured LLM classification.
    """
    # Try keyword classification first for speed
    if use_keywords:
        keyword_result = keyword_classify(message)
        if keyword_result:
            logger.info(f"Keyword classified '{message[:50]}...' as {keyword_result}")

            # Extract basic entities even with keyword match
            contract = extract_contract_number(message)
            entities = {}
            if contract:
                entities["contract_number"] = contract

            return StructuredClassification(
                category=keyword_result,
                confidence=0.85,
                entities=entities,
                ambiguous=False,
                urgency="normal",
                method="keyword",
            )

    # Fall back to structured LLM classification
    return await llm_classify_structured(message, context)


# ============================================
# Utilities
# ============================================

def extract_contract_number(message: str) -> str | None:
    """Extract contract/account number from message"""
    # Match 6-10 digit numbers
    match = re.search(r"\b(\d{6,10})\b", message)
    return match.group(1) if match else None


def extract_entities(message: str) -> dict[str, str | None]:
    """
    Extract common entities from message using regex.

    Args:
        message: Message to extract entities from

    Returns:
        Dictionary of extracted entities
    """
    entities: dict[str, str | None] = {}

    # Contract number (6-10 digits)
    contract_match = re.search(r"\b(\d{6,10})\b", message)
    if contract_match:
        entities["contract_number"] = contract_match.group(1)

    # Mexican phone (10 digits with optional +52)
    phone_match = re.search(
        r"(?:\+?52)?[\s.-]?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}",
        message,
    )
    if phone_match:
        entities["phone"] = phone_match.group()

    # Date patterns (dd/mm/yyyy or similar)
    date_match = re.search(
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        message,
    )
    if date_match:
        entities["date"] = date_match.group(1)

    # Email
    email_match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        message,
    )
    if email_match:
        entities["email"] = email_match.group()

    return entities


def get_category_description(category: str) -> str:
    """Get human-readable description for category."""
    data = _get_classifier_data()
    return data.category_descriptions.get(category, category)


def is_ambiguous_message(message: str) -> bool:
    """
    Check if message is too short/vague to reliably classify.

    Short responses like "si", "ok", "gracias" should continue with
    the current agent rather than being re-classified.
    """
    short_responses = {
        "si", "si", "no", "ok", "ya", "bueno", "claro", "vale",
        "gracias", "aja", "aja", "okey", "okay", "bien", "dale",
        "perfecto", "listo", "entendido", "de acuerdo", "esta bien",
        "esta bien", "muy bien", "ah ok", "ah ya", "sale",
    }
    cleaned = message.lower().strip().rstrip(".,!?")
    return len(cleaned) < 15 or cleaned in short_responses


def detect_urgency(message: str) -> str:
    """
    Detect urgency level from message content.

    Returns:
        "emergency", "high", or "normal"
    """
    lower = message.lower()

    # Emergency keywords
    emergency_keywords = [
        "violencia", "golpe", "amenaza", "peligro", "emergencia",
        "ayuda urgente", "auxilio", "socorro", "me estan",
    ]
    if any(kw in lower for kw in emergency_keywords):
        return "emergency"

    # High urgency keywords
    high_keywords = [
        "urgente", "corte manana", "plazo", "vence hoy",
        "no tengo agua", "sin servicio", "desde hace dias",
    ]
    if any(kw in lower for kw in high_keywords):
        return "high"

    return "normal"
