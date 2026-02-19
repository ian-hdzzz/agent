"""
Unit tests for orchestrator.classifier

Tests keyword classification for all 13 categories, ambiguity detection,
entity extraction, urgency detection, and structured classification fallbacks.
All LLM calls are mocked -- no external services required.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We test the public functions directly; they live in orchestrator.classifier
from orchestrator.classifier import (
    detect_urgency,
    extract_contract_number,
    extract_entities,
    get_category_description,
    is_ambiguous_message,
    keyword_classify,
)


# ===================================================================
# keyword_classify - All 13 categories
# ===================================================================

class TestKeywordClassify:
    """Test keyword_classify() for each category with Spanish inputs."""

    # -- CEA (Water) --------------------------------------------------

    def test_agua_basic(self):
        assert keyword_classify("Tengo una fuga de agua en mi calle") == "CEA"

    def test_agua_recibo(self):
        assert keyword_classify("Quiero mi recibo de agua") == "CEA"

    def test_agua_medidor(self):
        assert keyword_classify("El medidor de agua no funciona") == "CEA"

    def test_agua_drenaje(self):
        assert keyword_classify("Problema de drenaje en mi colonia") == "CEA"

    def test_agua_reconexion(self):
        assert keyword_classify("Necesito la reconexión del agua") == "CEA"

    # -- TRA (Transport) -----------------------------------------------

    def test_transporte_ruta(self):
        assert keyword_classify("Que ruta de autobus pasa por el centro") == "TRA"

    def test_transporte_camion(self):
        assert keyword_classify("A que hora pasa el camion 45") == "TRA"

    def test_transporte_tarjeta(self):
        assert keyword_classify("Como saco mi tarjeta preferente") == "TRA"

    def test_transporte_qrobus(self):
        assert keyword_classify("Horarios de qrobus") == "TRA"

    # -- EDU (Education) -----------------------------------------------

    def test_educacion_escuela(self):
        assert keyword_classify("Donde queda la escuela mas cercana") == "EDU"

    def test_educacion_inscripcion(self):
        assert keyword_classify("Cuando empiezan las preinscripcion") == "EDU"

    def test_educacion_usebeq(self):
        assert keyword_classify("Tramites de usebeq") == "EDU"

    # -- VEH (Vehicles) ------------------------------------------------

    def test_vehiculos_placas(self):
        assert keyword_classify("Necesito renovar mis placas") == "VEH"

    def test_vehiculos_multa(self):
        assert keyword_classify("Tengo una multa pendiente") == "VEH"

    def test_vehiculos_tenencia(self):
        assert keyword_classify("Donde pago la tenencia 2025") == "VEH"

    def test_vehiculos_licencia(self):
        assert keyword_classify("Como saco la licencia de conducir") == "VEH"

    # -- PSI (Psychology) -----------------------------------------------

    def test_psicologia_cita(self):
        assert keyword_classify("Necesito un psicologo") == "PSI"

    def test_psicologia_ansiedad(self):
        assert keyword_classify("Tengo mucha ansiedad") == "PSI"

    def test_psicologia_depresion(self):
        assert keyword_classify("Creo que tengo depresion") == "PSI"

    def test_psicologia_apoyo_emocional(self):
        assert keyword_classify("Busco apoyo emocional para mi hijo") == "PSI"

    # -- IQM (Women's Attention) ----------------------------------------

    def test_iqm_violencia(self):
        assert keyword_classify("Estoy sufriendo violencia familiar") == "IQM"

    def test_iqm_mujer(self):
        assert keyword_classify("Atencion a mujeres en Queretaro") == "IQM"

    def test_iqm_acoso(self):
        assert keyword_classify("Quiero denunciar acoso") == "IQM"

    # -- CUL (Culture) -------------------------------------------------

    def test_cultura_museo(self):
        assert keyword_classify("Horarios del museo de la ciudad") == "CUL"

    def test_cultura_evento(self):
        assert keyword_classify("Que evento cultural hay este fin de semana") == "CUL"

    def test_cultura_biblioteca(self):
        assert keyword_classify("Donde hay una biblioteca publica") == "CUL"

    # -- RPP (Public Registry) -----------------------------------------

    def test_rpp_certificado(self):
        assert keyword_classify("Necesito un certificado de gravamen del registro público") == "RPP"

    def test_rpp_propiedad(self):
        assert keyword_classify("Consulta inmobiliaria de mi propiedad") == "RPP"

    def test_rpp_herencia(self):
        assert keyword_classify("Tramite de herencia de inmueble") == "RPP"

    # -- LAB (Labor) ---------------------------------------------------

    def test_laboral_despido(self):
        assert keyword_classify("Tuve un despido injusto y quiero demanda laboral") == "LAB"

    def test_laboral_demanda(self):
        assert keyword_classify("Como pongo una demanda laboral") == "LAB"

    def test_laboral_finiquito(self):
        assert keyword_classify("No me quieren dar mi finiquito") == "LAB"

    # -- VIV (Housing) -------------------------------------------------

    def test_vivienda_credito(self):
        assert keyword_classify("Como aplico para un credito hipotecario") == "VIV"

    def test_vivienda_iveq(self):
        assert keyword_classify("Programas de vivienda del iveq") == "VIV"

    def test_vivienda_escrituras(self):
        assert keyword_classify("Necesito escriturar mi vivienda") == "VIV"

    # -- APP (APPQRO) --------------------------------------------------

    def test_app_error(self):
        assert keyword_classify("La app no funciona") == "APP"

    def test_app_descargar(self):
        assert keyword_classify("Donde descargo la aplicacion appqro") == "APP"

    # -- SOC (Social Programs) -----------------------------------------

    def test_social_apoyo(self):
        assert keyword_classify("Como me inscribo a un programa social") == "SOC"

    def test_social_tarjeta_contigo(self):
        assert keyword_classify("Tengo problemas con mi tarjeta contigo") == "SOC"

    # -- ATC (Citizen Attention) ----------------------------------------

    def test_atc_queja(self):
        assert keyword_classify("Quiero poner una queja general") == "ATC"

    def test_atc_contactanos(self):
        assert keyword_classify("contactanos por favor") == "ATC"

    # -- EXIT -----------------------------------------------------------

    def test_exit_gracias(self):
        assert keyword_classify("gracias por la ayuda") == "EXIT"

    def test_exit_adios(self):
        assert keyword_classify("adios, hasta luego") == "EXIT"

    def test_exit_bye(self):
        assert keyword_classify("bye") == "EXIT"

    # -- None (ambiguous / no keyword match) ----------------------------

    def test_no_match_gibberish(self):
        assert keyword_classify("xyzzy lorem ipsum") is None

    def test_no_match_generic_greeting(self):
        assert keyword_classify("hola buen dia") is None

    # -- Ambiguous multi-category (close scores -> None) -----------------

    def test_ambiguous_multi_category(self):
        # "agua" -> CEA, "violencia" -> IQM -- scores tied
        result = keyword_classify("hay violencia y no hay agua")
        # Both hit 1 keyword each, scores equal -> should be None
        assert result is None

    # -- Clear winner despite multiple mentions -------------------------

    def test_clear_winner_multiple_keywords(self):
        msg = "tengo fuga de agua, mi medidor esta roto y necesito reconexion del drenaje"
        assert keyword_classify(msg) == "CEA"


# ===================================================================
# is_ambiguous_message
# ===================================================================

class TestIsAmbiguousMessage:
    """Test ambiguity detection for short/vague responses."""

    @pytest.mark.parametrize("msg", [
        "si", "Si", "SI",
        "no", "ok", "ya", "bueno",
        "gracias", "perfecto", "listo",
        "entendido", "de acuerdo", "dale",
        "okey", "bien", "claro",
    ])
    def test_short_responses_are_ambiguous(self, msg):
        assert is_ambiguous_message(msg) is True

    @pytest.mark.parametrize("msg", [
        "Quiero consultar mi recibo de agua del contrato 123456",
        "Necesito saber cuanto debo de placas QRO-1234",
        "Me pueden dar los horarios de la ruta 45 del autobus",
    ])
    def test_clear_messages_are_not_ambiguous(self, msg):
        assert is_ambiguous_message(msg) is False

    def test_punctuation_stripped(self):
        assert is_ambiguous_message("ok!") is True
        assert is_ambiguous_message("si?") is True

    def test_short_but_unknown_word(self):
        # Under 15 chars is ambiguous regardless of content
        assert is_ambiguous_message("hola") is True

    def test_exact_15_chars_not_ambiguous(self):
        # "quiero mi agua!" is 15 chars after strip  -> not ambiguous
        msg = "quiero mi aguas"
        assert len(msg.strip()) == 15
        assert is_ambiguous_message(msg) is False


# ===================================================================
# extract_contract_number
# ===================================================================

class TestExtractContractNumber:
    """Test contract number extraction from messages."""

    def test_extract_6_digit(self):
        assert extract_contract_number("mi contrato es 123456") == "123456"

    def test_extract_10_digit(self):
        assert extract_contract_number("contrato 1234567890") == "1234567890"

    def test_no_match_short(self):
        assert extract_contract_number("codigo 12345") is None

    def test_no_match_too_long(self):
        assert extract_contract_number("numero 12345678901") is None

    def test_no_numbers(self):
        assert extract_contract_number("quiero consultar mi agua") is None

    def test_extracts_first_match(self):
        result = extract_contract_number("contrato 123456 y contrato 654321")
        assert result == "123456"


# ===================================================================
# extract_entities
# ===================================================================

class TestExtractEntities:
    """Test entity extraction from messages."""

    def test_extract_contract(self):
        entities = extract_entities("Mi contrato es 1234567")
        assert entities.get("contract_number") == "1234567"

    def test_extract_email(self):
        entities = extract_entities("Mi correo es juan@gmail.com")
        assert entities.get("email") == "juan@gmail.com"

    def test_extract_date(self):
        entities = extract_entities("La cita es el 15/03/2025")
        assert entities.get("date") == "15/03/2025"

    def test_no_entities(self):
        entities = extract_entities("hola buen dia")
        assert entities == {}


# ===================================================================
# detect_urgency
# ===================================================================

class TestDetectUrgency:
    """Test urgency level detection."""

    def test_emergency_violencia(self):
        assert detect_urgency("Me estan golpeando, necesito ayuda") == "emergency"

    def test_emergency_amenaza(self):
        assert detect_urgency("Recibo amenaza de muerte") == "emergency"

    def test_high_urgente(self):
        assert detect_urgency("Es urgente, necesito respuesta hoy") == "high"

    def test_high_no_tengo_agua(self):
        assert detect_urgency("No tengo agua desde hace tres dias") == "high"

    def test_normal_regular(self):
        assert detect_urgency("Quiero consultar mi saldo") == "normal"


# ===================================================================
# get_category_description
# ===================================================================

class TestGetCategoryDescription:
    """Test human-readable category descriptions."""

    def test_all_categories_have_description(self):
        categories = [
            "CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL",
            "RPP", "LAB", "VIV", "APP", "SOC", "ATC", "EXIT",
        ]
        for cat in categories:
            desc = get_category_description(cat)
            assert isinstance(desc, str)
            assert len(desc) > 0
            assert desc != cat  # Should be human-readable, not just the code

    def test_unknown_category_returns_code(self):
        assert get_category_description("ZZZ") == "ZZZ"


# ===================================================================
# LLM classify (mocked)
# ===================================================================

class TestLLMClassify:
    """Test LLM-based classification with mocked Anthropic client."""

    @pytest.mark.asyncio
    async def test_llm_classify_returns_valid_category(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        set_response("CEA")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify
            result = await llm_classify("mi agua esta cortada")

        assert result["category"] == "CEA"
        assert result["method"] == "llm"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_llm_classify_fallback_on_error(self, mock_anthropic_client):
        client, _ = mock_anthropic_client
        client.messages.create.side_effect = Exception("API down")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify
            result = await llm_classify("algo raro")

        assert result["category"] == "ATC"
        assert result["method"] == "fallback"
        assert result["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_llm_classify_atc_default_confidence(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        set_response("ATC")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify
            result = await llm_classify("no se que necesito")

        assert result["category"] == "ATC"
        assert result["confidence"] == 0.5  # lower confidence for ATC default


# ===================================================================
# classify_intent (keyword + LLM pipeline)
# ===================================================================

class TestClassifyIntent:
    """Test the main classify_intent pipeline."""

    @pytest.mark.asyncio
    async def test_keyword_match_skips_llm(self):
        from orchestrator.classifier import classify_intent
        result = await classify_intent("tengo una fuga de agua grande")
        assert result["category"] == "CEA"
        assert result["method"] == "keyword"
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_no_keyword_falls_to_llm(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        set_response("TRA")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import classify_intent
            result = await classify_intent("como me muevo por la ciudad")

        assert result["category"] == "TRA"
        assert result["method"] == "llm"

    @pytest.mark.asyncio
    async def test_use_keywords_false_forces_llm(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        set_response("CEA")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import classify_intent
            # Even though "agua" would match keyword, force LLM
            result = await classify_intent("tengo una fuga de agua", use_keywords=False)

        assert result["method"] == "llm"


# ===================================================================
# Structured LLM classification (mocked)
# ===================================================================

class TestLLMClassifyStructured:
    """Test structured classification with entity extraction."""

    @pytest.mark.asyncio
    async def test_structured_classify_parses_json(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        json_response = json.dumps({
            "category": "CEA",
            "confidence": 0.95,
            "entities": {"contract_number": "123456"},
            "ambiguous": False,
            "urgency": "normal",
        })
        set_response(json_response)

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify_structured
            result = await llm_classify_structured("mi contrato 123456 tiene agua cortada")

        assert result.category == "CEA"
        assert result.confidence == 0.95
        assert result.entities.get("contract_number") == "123456"
        assert result.ambiguous is False
        assert result.method == "llm_structured"

    @pytest.mark.asyncio
    async def test_structured_classify_handles_markdown_json(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        # LLM sometimes wraps JSON in markdown code blocks
        wrapped = '```json\n{"category":"VEH","confidence":0.9,"entities":{},"ambiguous":false,"urgency":"normal"}\n```'
        set_response(wrapped)

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify_structured
            result = await llm_classify_structured("cuanto debo de placas")

        assert result.category == "VEH"

    @pytest.mark.asyncio
    async def test_structured_classify_fallback_on_bad_json(self, mock_anthropic_client):
        client, set_response = mock_anthropic_client
        set_response("this is not JSON at all")

        with patch("orchestrator.classifier.Anthropic", return_value=client), \
             patch("orchestrator.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.model = "claude-sonnet-4-5-20250929"
            mock_settings.classification_temperature = 0.1

            from orchestrator.classifier import llm_classify_structured
            result = await llm_classify_structured("algo")

        assert result.category == "ATC"
        assert result.method == "fallback"
        assert result.ambiguous is True
