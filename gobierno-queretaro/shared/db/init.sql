-- ============================================
-- Gobierno Querétaro - Database Initialization
-- Multi-Agent State Management
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Agent Registry (Dynamic, self-registering)
-- ============================================
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    endpoint VARCHAR(255),
    category_code VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    -- New fields for dynamic registry
    version VARCHAR(20) DEFAULT '1.0.0',
    confidentiality_level VARCHAR(20) DEFAULT 'INTERNAL',  -- PUBLIC | INTERNAL | CONFIDENTIAL | SECRET
    sla_tier VARCHAR(20) DEFAULT 'standard',               -- critical | standard | best_effort
    capabilities JSONB DEFAULT '{}',                        -- AgentCapabilities JSON
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    registered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category_code);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active);
CREATE INDEX IF NOT EXISTS idx_agents_sla ON agents(sla_tier);

-- Insert all 13 government agents (seed data, agents self-register on startup)
-- capabilities includes classification metadata (keywords, classification_hint, category_description)
-- so the orchestrator classifier can build its data dynamically from the registry
INSERT INTO agents (id, name, description, category_code, endpoint, version, confidentiality_level, sla_tier, capabilities) VALUES
    ('water-cea', 'Agente de Agua - CEA', 'Servicios de agua: consultas, fugas, consumos, reconexion', 'CEA', 'http://agent-water-cea:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "optional_context": ["contract_number", "contact_id"], "keywords": ["agua", "fuga", "fugas", "deuda de agua", "consumo de agua", "recibo de agua", "medidor", "alcantarillado", "drenaje", "reconexion", "corte de agua", "no hay agua", "agua turbia", "cea", "saldo de agua", "aclaracion agua", "contrato agua", "lectura medidor", "recibo digital agua"], "classification_hint": "agua, fugas, deuda de agua, consumos, reconexion, medidor, alcantarillado", "category_description": "Servicios de Agua (CEA)"}'),
    ('transport-ameq', 'Agente de Transporte - AMEQ', 'Rutas, horarios y servicios de autobus', 'TRA', 'http://agent-transport-ameq:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["autobus", "camion", "ruta", "transporte", "parada", "horario de camion", "tarjeta de transporte", "ameq", "transporte publico", "qrobus", "qro bus", "tarjeta preferente", "tarjeta estudiante", "credencial estudiante", "adulto mayor transporte", "inapam transporte", "tercera edad transporte", "persona con discapacidad transporte", "discapacidad transporte", "nino 3 a 6", "tarifa unidos", "tarifa $2", "tarifa 2 pesos", "tarjeta prepago", "saldo tarjeta transporte", "historial tarjeta", "recargar tarjeta", "recarga qrobus", "como llego", "que ruta", "punto a punto", "mapa ruta", "descargar mapa ruta", "permiso transporte", "concesion transporte", "tio transporte", "tramites vehiculo transporte", "evaluar transporte", "sugerir transporte", "iqt", "iqtapp"], "classification_hint": "rutas de autobus, horarios, tarjetas de transporte, paradas", "category_description": "Transporte Publico (AMEQ)"}'),
    ('education-usebeq', 'Agente de Educacion - USEBEQ', 'Escuelas, inscripciones, becas educativas', 'EDU', 'http://agent-education-usebeq:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["escuela", "inscripcion", "preinscripcion", "educacion", "usebeq", "colegio", "preparatoria", "secundaria", "primaria", "vinculacion parental", "vinculacion", "verifica vinculacion", "curp aspirante", "preasignacion", "said", "asesoria educativa", "ciclo escolar"], "classification_hint": "escuelas, inscripciones, becas educativas, constancias escolares", "category_description": "Educacion (USEBEQ)"}'),
    ('vehicles', 'Agente de Tramites Vehiculares', 'Placas, multas, registro vehicular', 'VEH', 'http://agent-vehicles:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["placa", "placas", "multa", "multas", "licencia de conducir", "registro vehicular", "tenencia", "verificacion", "carro", "vehiculo", "auto", "motocicleta", "pago tenencia", "tenencia 2026", "tenencia 2025", "oficina recaudadora", "consulta pago vehiculo", "comprobante pago vehiculo", "descarga comprobante", "preguntas frecuentes tenencia", "sustitucion placa", "placa perdida", "placa lluvia", "placa desgastada", "reposicion placa", "portal tributario"], "classification_hint": "placas, multas de transito, licencias de conducir, registro vehicular", "category_description": "Tramites Vehiculares"}'),
    ('psychology-sejuve', 'Agente de Psicologia - SEJUVE', 'Citas, salud mental, orientacion', 'PSI', 'http://agent-psychology-sejuve:8000', '1.0.0', 'CONFIDENTIAL', 'critical',
     '{"can_handoff_to": ["human"], "required_context": ["conversation_id"], "keywords": ["psicologo", "psicologia", "salud mental", "ansiedad", "depresion", "terapia", "sejuve", "orientacion juvenil", "cita psicologica", "ser tranquilidad", "primeros auxilios emocionales", "atencion psicologica", "apoyo emocional"], "classification_hint": "citas psicologicas, salud mental, orientacion juvenil", "category_description": "Psicologia (SEJUVE)"}'),
    ('women-iqm', 'Agente de Atencion a Mujeres - IQM', 'Apoyo, violencia de genero, orientacion', 'IQM', 'http://agent-women-iqm:8000', '1.0.0', 'SECRET', 'critical',
     '{"can_handoff_to": ["human"], "required_context": ["conversation_id"], "keywords": ["violencia", "mujer", "mujeres", "genero", "acoso", "maltrato", "iqm", "atencion a mujeres", "asesoria legal mujer", "refugio", "violencia domestica", "violencia familiar", "tel mujer", "4422164757", "instituto queretano de la mujer", "centros atencion mujer", "pasos ante violencia", "asesoria legal iqm", "asesoria psicologica iqm"], "classification_hint": "apoyo a mujeres, violencia de genero, orientacion legal", "category_description": "Atencion a Mujeres (IQM)"}'),
    ('culture', 'Agente de Cultura', 'Eventos, talleres, becas culturales', 'CUL', 'http://agent-culture:8000', '1.0.0', 'PUBLIC', 'best_effort',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["cultura", "museo", "museos", "teatro", "taller cultural", "evento", "concierto", "exposicion", "biblioteca", "arte", "beca cultural", "danza", "musica", "pintura", "centro cultural", "galeria libertad", "arte emergente", "centro artes queretaro", "casa del faldon", "casa faldon", "centro queretano imagen", "museo arte contemporaneo", "museo arte queretaro", "museo ciudad", "museo conspiradores", "museo restauracion", "museo anbanica", "museo sierra gorda", "museo pinal amoles", "secretaria cultura", "cartelera cultural", "la cultura esta en nosotros"], "classification_hint": "eventos culturales, talleres, becas artisticas, museos, bibliotecas", "category_description": "Cultura"}'),
    ('registry-rpp', 'Agente de Registro Publico - RPP', 'Documentos, certificados, tramites', 'RPP', 'http://agent-registry-rpp:8000', '1.0.0', 'CONFIDENTIAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["registro publico", "rpp", "propiedad", "inmueble", "consulta inmobiliaria", "cerlin", "clave catastral", "folio inmueble", "certificado gravamen", "libertad gravamen", "certificado inscripcion", "certificado propiedad", "unica propiedad", "no propiedad", "historial registral", "busqueda antecedentes", "copias certificadas", "cancelacion hipoteca", "infonavit cancelar", "fovissste cancelar", "cancelacion caducidad", "demanda embargo", "inscripcion judicial", "validacion testamento", "validez testamento", "nombramiento albacea", "herencia", "alerta registral", "seguimiento tramite rpp", "horario rpp", "ubicacion rpp", "costos rpp", "aclaraciones rpp", "rechazo certificado"], "classification_hint": "documentos oficiales, certificados, actas de nacimiento", "category_description": "Registro Publico (RPP)"}'),
    ('labor-cclq', 'Agente de Conciliacion Laboral - CCLQ', 'Demandas laborales, conciliacion', 'LAB', 'http://agent-labor-cclq:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["trabajo", "despido", "demanda laboral", "conciliacion laboral", "derechos laborales", "finiquito", "liquidacion", "cclq", "junta de conciliacion", "asesoria juridica laboral", "proceso conciliacion", "convenio laboral", "ratificacion convenio", "asunto colectivo", "sindicato", "procuraduria defensa trabajo", "asunto anterior noviembre 2021", "asunto anterior 2021"], "classification_hint": "demandas laborales, despidos, derechos del trabajador", "category_description": "Conciliacion Laboral (CCLQ)"}'),
    ('housing-iveq', 'Agente de Vivienda - IVEQ', 'Creditos, programas de vivienda', 'VIV', 'http://agent-housing-iveq:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "women-iqm", "human"], "required_context": ["conversation_id"], "keywords": ["vivienda", "casa", "credito hipotecario", "iveq", "programa de vivienda", "terreno", "lote", "escrituras", "subsidio vivienda", "constancia no adeudo vivienda", "expedicion planos", "cesion derechos", "emision instruccion notarial", "autoproduccion", "autoproduccion municipios", "vivienda trabajadores estado", "juntos por tu vivienda", "escriturar iveq", "regularizacion vivienda", "cita iveq"], "classification_hint": "creditos de vivienda, programas habitacionales", "category_description": "Vivienda (IVEQ)"}'),
    ('appqro', 'Agente de Soporte APPQRO', 'Soporte tecnico de la app', 'APP', 'http://agent-appqro:8000', '1.0.0', 'PUBLIC', 'best_effort',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["app", "aplicacion", "appqro", "error en app", "no funciona la app", "actualizar app", "descargar app", "problema con la aplicacion", "informacion appqro", "ayuda appqro", "contactar agente app"], "classification_hint": "soporte tecnico de la aplicacion movil del gobierno", "category_description": "Soporte APPQRO"}'),
    ('social-sedesoq', 'Agente de Programas Sociales - SEDESOQ', 'Beneficios, ayudas, programas sociales', 'SOC', 'http://agent-social-sedesoq:8000', '1.0.0', 'INTERNAL', 'standard',
     '{"can_handoff_to": ["citizen-attention", "human"], "required_context": ["conversation_id"], "keywords": ["programa social", "apoyo economico", "beneficio", "sedesoq", "despensa", "beca social", "tarjeta contigo", "problemas tarjeta contigo"], "classification_hint": "beneficios sociales, ayudas economicas, apoyos", "category_description": "Programas Sociales (SEDESOQ)"}'),
    ('citizen-attention', 'Agente de Atencion Ciudadana', 'Quejas, sugerencias, PQRS', 'ATC', 'http://agent-citizen-attention:8000', '1.0.0', 'INTERNAL', 'best_effort',
     '{"can_handoff_to": ["human"], "required_context": ["conversation_id"], "keywords": ["atencion ciudadana", "contactanos", "4421015205", "queja general", "sugerencia general", "informacion general"], "classification_hint": "quejas generales, sugerencias, PQRS que no encajan en otro", "category_description": "Atencion Ciudadana"}')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    endpoint = EXCLUDED.endpoint,
    version = EXCLUDED.version,
    confidentiality_level = EXCLUDED.confidentiality_level,
    sla_tier = EXCLUDED.sla_tier,
    capabilities = EXCLUDED.capabilities,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- Conversation State
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100), -- Chatwoot conversation ID
    contact_id VARCHAR(100),  -- Chatwoot contact ID
    current_agent_id VARCHAR(50) REFERENCES agents(id),
    state JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_external_id ON conversations(external_id);
CREATE INDEX IF NOT EXISTS idx_conversations_contact_id ON conversations(contact_id);

-- ============================================
-- Message History
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    agent_id VARCHAR(50) REFERENCES agents(id),
    tools_used JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- ============================================
-- Tasks (Multi-step workflows)
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    agent_id VARCHAR(50) REFERENCES agents(id),
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed, failed
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    subtasks JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tasks_conversation_id ON tasks(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ============================================
-- Events (For pub/sub and audit)
-- ============================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    source_agent_id VARCHAR(50) REFERENCES agents(id),
    target_agent_id VARCHAR(50) REFERENCES agents(id),
    conversation_id UUID REFERENCES conversations(id),
    payload JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_processed ON events(processed);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- ============================================
-- Tickets (Government Service Requests)
-- ============================================
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    folio VARCHAR(20) UNIQUE NOT NULL,
    conversation_id UUID REFERENCES conversations(id),
    agent_id VARCHAR(50) REFERENCES agents(id),
    category_code VARCHAR(10) NOT NULL,
    subcategory_code VARCHAR(20),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'open', -- open, in_progress, resolved, closed, cancelled
    priority VARCHAR(10) DEFAULT 'medium', -- low, medium, high, urgent
    contact_info JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tickets_folio ON tickets(folio);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category_code);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);

-- ============================================
-- Function to generate ticket folio
-- ============================================
CREATE OR REPLACE FUNCTION generate_ticket_folio()
RETURNS TRIGGER AS $$
DECLARE
    prefix VARCHAR(3);
    seq_num INTEGER;
BEGIN
    -- Get category prefix
    prefix := NEW.category_code;

    -- Get next sequence number for this category today
    SELECT COALESCE(MAX(CAST(SUBSTRING(folio FROM 12) AS INTEGER)), 0) + 1
    INTO seq_num
    FROM tickets
    WHERE category_code = NEW.category_code
    AND DATE(created_at) = CURRENT_DATE;

    -- Generate folio: PREFIX-YYYYMMDD-NNNN
    NEW.folio := prefix || '-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD(seq_num::TEXT, 4, '0');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_generate_folio
BEFORE INSERT ON tickets
FOR EACH ROW
WHEN (NEW.folio IS NULL)
EXECUTE FUNCTION generate_ticket_folio();

-- ============================================
-- Update timestamp function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_conversations_updated
BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trigger_tasks_updated
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trigger_tickets_updated
BEFORE UPDATE ON tickets
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trigger_agents_updated
BEFORE UPDATE ON agents
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- LangGraph Checkpoints (for crash recovery)
-- Compatible with langgraph PostgresSaver schema
-- ============================================
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
    checkpoint_id VARCHAR(255) NOT NULL,
    parent_checkpoint_id VARCHAR(255),
    type VARCHAR(255),
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
    checkpoint_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    idx INTEGER NOT NULL,
    channel VARCHAR(255) NOT NULL,
    type VARCHAR(255),
    value JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
    channel VARCHAR(255) NOT NULL,
    version VARCHAR(255) NOT NULL,
    type VARCHAR(255),
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
