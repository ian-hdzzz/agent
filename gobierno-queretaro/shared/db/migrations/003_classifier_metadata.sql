-- ============================================
-- Migration 003: Add classifier metadata to agent capabilities
--
-- Adds keywords, classification_hint, and category_description
-- to each agent's capabilities JSONB field so the orchestrator
-- classifier can build its data dynamically from the registry.
-- ============================================

-- CEA - Water
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["agua", "fuga", "fugas", "deuda de agua", "consumo de agua", "recibo de agua", "medidor", "alcantarillado", "drenaje", "reconexion", "corte de agua", "no hay agua", "agua turbia", "cea", "saldo de agua", "aclaracion agua", "contrato agua", "lectura medidor", "recibo digital agua"],
    "classification_hint": "agua, fugas, deuda de agua, consumos, reconexion, medidor, alcantarillado",
    "category_description": "Servicios de Agua (CEA)"
}'::jsonb WHERE id = 'water-cea';

-- TRA - Transport
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["autobus", "camion", "ruta", "transporte", "parada", "horario de camion", "tarjeta de transporte", "ameq", "transporte publico", "qrobus", "qro bus", "tarjeta preferente", "tarjeta estudiante", "credencial estudiante", "adulto mayor transporte", "inapam transporte", "tercera edad transporte", "persona con discapacidad transporte", "discapacidad transporte", "nino 3 a 6", "tarifa unidos", "tarifa $2", "tarifa 2 pesos", "tarjeta prepago", "saldo tarjeta transporte", "historial tarjeta", "recargar tarjeta", "recarga qrobus", "como llego", "que ruta", "punto a punto", "mapa ruta", "descargar mapa ruta", "permiso transporte", "concesion transporte", "tio transporte", "tramites vehiculo transporte", "evaluar transporte", "sugerir transporte", "iqt", "iqtapp"],
    "classification_hint": "rutas de autobus, horarios, tarjetas de transporte, paradas",
    "category_description": "Transporte Publico (AMEQ)"
}'::jsonb WHERE id = 'transport-ameq';

-- EDU - Education
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["escuela", "inscripcion", "preinscripcion", "educacion", "usebeq", "colegio", "preparatoria", "secundaria", "primaria", "vinculacion parental", "vinculacion", "verifica vinculacion", "curp aspirante", "preasignacion", "said", "asesoria educativa", "ciclo escolar"],
    "classification_hint": "escuelas, inscripciones, becas educativas, constancias escolares",
    "category_description": "Educacion (USEBEQ)"
}'::jsonb WHERE id = 'education-usebeq';

-- VEH - Vehicles
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["placa", "placas", "multa", "multas", "licencia de conducir", "registro vehicular", "tenencia", "verificacion", "carro", "vehiculo", "auto", "motocicleta", "pago tenencia", "tenencia 2026", "tenencia 2025", "oficina recaudadora", "consulta pago vehiculo", "comprobante pago vehiculo", "descarga comprobante", "preguntas frecuentes tenencia", "sustitucion placa", "placa perdida", "placa lluvia", "placa desgastada", "reposicion placa", "portal tributario"],
    "classification_hint": "placas, multas de transito, licencias de conducir, registro vehicular",
    "category_description": "Tramites Vehiculares"
}'::jsonb WHERE id = 'vehicles';

-- PSI - Psychology
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["psicologo", "psicologia", "salud mental", "ansiedad", "depresion", "terapia", "sejuve", "orientacion juvenil", "cita psicologica", "ser tranquilidad", "primeros auxilios emocionales", "atencion psicologica", "apoyo emocional"],
    "classification_hint": "citas psicologicas, salud mental, orientacion juvenil",
    "category_description": "Psicologia (SEJUVE)"
}'::jsonb WHERE id = 'psychology-sejuve';

-- IQM - Women
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["violencia", "mujer", "mujeres", "genero", "acoso", "maltrato", "iqm", "atencion a mujeres", "asesoria legal mujer", "refugio", "violencia domestica", "violencia familiar", "tel mujer", "4422164757", "instituto queretano de la mujer", "centros atencion mujer", "pasos ante violencia", "asesoria legal iqm", "asesoria psicologica iqm"],
    "classification_hint": "apoyo a mujeres, violencia de genero, orientacion legal",
    "category_description": "Atencion a Mujeres (IQM)"
}'::jsonb WHERE id = 'women-iqm';

-- CUL - Culture
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["cultura", "museo", "museos", "teatro", "taller cultural", "evento", "concierto", "exposicion", "biblioteca", "arte", "beca cultural", "danza", "musica", "pintura", "centro cultural", "galeria libertad", "arte emergente", "centro artes queretaro", "casa del faldon", "casa faldon", "centro queretano imagen", "museo arte contemporaneo", "museo arte queretaro", "museo ciudad", "museo conspiradores", "museo restauracion", "museo anbanica", "museo sierra gorda", "museo pinal amoles", "secretaria cultura", "cartelera cultural", "la cultura esta en nosotros"],
    "classification_hint": "eventos culturales, talleres, becas artisticas, museos, bibliotecas",
    "category_description": "Cultura"
}'::jsonb WHERE id = 'culture';

-- RPP - Registry
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["registro publico", "rpp", "propiedad", "inmueble", "consulta inmobiliaria", "cerlin", "clave catastral", "folio inmueble", "certificado gravamen", "libertad gravamen", "certificado inscripcion", "certificado propiedad", "unica propiedad", "no propiedad", "historial registral", "busqueda antecedentes", "copias certificadas", "cancelacion hipoteca", "infonavit cancelar", "fovissste cancelar", "cancelacion caducidad", "demanda embargo", "inscripcion judicial", "validacion testamento", "validez testamento", "nombramiento albacea", "herencia", "alerta registral", "seguimiento tramite rpp", "horario rpp", "ubicacion rpp", "costos rpp", "aclaraciones rpp", "rechazo certificado"],
    "classification_hint": "documentos oficiales, certificados, actas de nacimiento",
    "category_description": "Registro Publico (RPP)"
}'::jsonb WHERE id = 'registry-rpp';

-- LAB - Labor
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["trabajo", "despido", "demanda laboral", "conciliacion laboral", "derechos laborales", "finiquito", "liquidacion", "cclq", "junta de conciliacion", "asesoria juridica laboral", "proceso conciliacion", "convenio laboral", "ratificacion convenio", "asunto colectivo", "sindicato", "procuraduria defensa trabajo", "asunto anterior noviembre 2021", "asunto anterior 2021"],
    "classification_hint": "demandas laborales, despidos, derechos del trabajador",
    "category_description": "Conciliacion Laboral (CCLQ)"
}'::jsonb WHERE id = 'labor-cclq';

-- VIV - Housing
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["vivienda", "casa", "credito hipotecario", "iveq", "programa de vivienda", "terreno", "lote", "escrituras", "subsidio vivienda", "constancia no adeudo vivienda", "expedicion planos", "cesion derechos", "emision instruccion notarial", "autoproduccion", "autoproduccion municipios", "vivienda trabajadores estado", "juntos por tu vivienda", "escriturar iveq", "regularizacion vivienda", "cita iveq"],
    "classification_hint": "creditos de vivienda, programas habitacionales",
    "category_description": "Vivienda (IVEQ)"
}'::jsonb WHERE id = 'housing-iveq';

-- APP - APPQRO
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["app", "aplicacion", "appqro", "error en app", "no funciona la app", "actualizar app", "descargar app", "problema con la aplicacion", "informacion appqro", "ayuda appqro", "contactar agente app"],
    "classification_hint": "soporte tecnico de la aplicacion movil del gobierno",
    "category_description": "Soporte APPQRO"
}'::jsonb WHERE id = 'appqro';

-- SOC - Social
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["programa social", "apoyo economico", "beneficio", "sedesoq", "despensa", "beca social", "tarjeta contigo", "problemas tarjeta contigo"],
    "classification_hint": "beneficios sociales, ayudas economicas, apoyos",
    "category_description": "Programas Sociales (SEDESOQ)"
}'::jsonb WHERE id = 'social-sedesoq';

-- ATC - Citizen Attention
UPDATE agents SET capabilities = capabilities || '{
    "keywords": ["atencion ciudadana", "contactanos", "4421015205", "queja general", "sugerencia general", "informacion general"],
    "classification_hint": "quejas generales, sugerencias, PQRS que no encajan en otro",
    "category_description": "Atencion Ciudadana"
}'::jsonb WHERE id = 'citizen-attention';
