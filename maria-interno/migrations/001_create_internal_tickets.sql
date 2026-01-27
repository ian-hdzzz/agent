-- ============================================
-- Maria Interno - Database Schema
-- Create tables for internal ticket system
-- ============================================

-- Internal Ticket Categories
CREATE TABLE IF NOT EXISTS internal_ticket_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    area_responsable VARCHAR(100),
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Internal Ticket Subcategories
CREATE TABLE IF NOT EXISTS internal_ticket_subcategories (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES internal_ticket_categories(id),
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_priority VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Employees Table (if not exists)
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    numero_empleado VARCHAR(20) UNIQUE,
    nombre VARCHAR(200) NOT NULL,
    email VARCHAR(200) UNIQUE,
    area VARCHAR(100),
    puesto VARCHAR(100),
    extension VARCHAR(20),
    ubicacion VARCHAR(200),
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Internal Tickets Table
CREATE TABLE IF NOT EXISTS internal_tickets (
    id SERIAL PRIMARY KEY,
    folio VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'medium',

    -- Category references
    category_code VARCHAR(10),
    subcategory_code VARCHAR(20),
    internal_category_id INTEGER REFERENCES internal_ticket_categories(id),
    internal_subcategory_id INTEGER REFERENCES internal_ticket_subcategories(id),

    -- Employee information
    employee_id VARCHAR(50),
    employee_name VARCHAR(200),
    employee_email VARCHAR(200),
    area_solicitante VARCHAR(100),
    ubicacion VARCHAR(200),

    -- Assignment
    assigned_to VARCHAR(200),
    assigned_at TIMESTAMP,

    -- Resolution
    resolved_at TIMESTAMP,
    resolution_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_internal_tickets_folio ON internal_tickets(folio);
CREATE INDEX IF NOT EXISTS idx_internal_tickets_status ON internal_tickets(status);
CREATE INDEX IF NOT EXISTS idx_internal_tickets_category ON internal_tickets(category_code);
CREATE INDEX IF NOT EXISTS idx_internal_tickets_employee_email ON internal_tickets(employee_email);
CREATE INDEX IF NOT EXISTS idx_internal_tickets_employee_id ON internal_tickets(employee_id);
CREATE INDEX IF NOT EXISTS idx_internal_tickets_created_at ON internal_tickets(created_at DESC);

-- ============================================
-- Insert Default Categories
-- ============================================

INSERT INTO internal_ticket_categories (code, name, description, area_responsable) VALUES
    ('TI', 'Tecnologías de la Información', 'Soporte técnico, equipos, sistemas, correo, redes y telefonía', 'Sistemas'),
    ('RH', 'Recursos Humanos', 'Solicitudes y trámites de personal', 'Capital Humano'),
    ('MNT', 'Mantenimiento de Instalaciones', 'Servicios de mantenimiento a oficinas y edificios', 'Servicios Generales'),
    ('VEH', 'Vehículos y Transporte', 'Solicitudes relacionadas con la flotilla vehicular', 'Transporte'),
    ('ALM', 'Almacén y Suministros', 'Solicitudes de materiales e insumos', 'Almacén'),
    ('ADM', 'Administrativo', 'Trámites administrativos internos', 'Administración'),
    ('COM', 'Comunicación Social', 'Solicitudes al área de comunicación', 'Comunicación'),
    ('JUR', 'Jurídico', 'Solicitudes al área legal', 'Jurídico'),
    ('SEG', 'Seguridad Institucional', 'Solicitudes de seguridad y vigilancia', 'Seguridad')
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert TI Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('TI-EQC', 'Falla de equipo de cómputo', 'PC, laptop, monitor no enciende, pantalla azul, lentitud extrema', 'high'),
    ('TI-SOF', 'Instalación de software', 'Instalación de programas, actualizaciones, licencias', 'medium'),
    ('TI-RED', 'Problemas de red/Internet', 'Sin conexión, Internet lento, WiFi no funciona', 'high'),
    ('TI-COR', 'Correo electrónico', 'No puede enviar/recibir correo, buzón lleno, configuración Outlook', 'medium'),
    ('TI-ACC', 'Accesos a sistemas', 'Alta de usuario, reset de contraseña, permisos, acceso a carpetas', 'medium'),
    ('TI-IMP', 'Impresoras', 'Impresora no imprime, atascos, configuración, tóner', 'low'),
    ('TI-TEL', 'Telefonía IP', 'Teléfono no funciona, extensión, buzón de voz', 'medium'),
    ('TI-SIS', 'Falla de sistema interno', 'Sistema lento, error en aplicación, módulo no funciona', 'high'),
    ('TI-WEB', 'Portal/Página web', 'Error en portal, actualización de contenido web', 'medium'),
    ('TI-BAC', 'Respaldo de información', 'Solicitud de respaldo, recuperación de archivos', 'medium'),
    ('TI-NUE', 'Equipo nuevo', 'Solicitud de equipo de cómputo nuevo, justificación', 'low'),
    ('TI-CAM', 'Cambio/Reasignación de equipo', 'Cambio de equipo entre empleados, reasignación', 'low'),
    ('TI-BAJ', 'Baja de equipo', 'Equipo obsoleto, para dar de baja del inventario', 'low'),
    ('TI-VPN', 'VPN/Acceso remoto', 'Configuración VPN, problemas de conexión remota', 'medium'),
    ('TI-SEG', 'Incidente de seguridad informática', 'Virus, ransomware, phishing, hackeo', 'urgent'),
    ('TI-CAP', 'Capacitación en sistemas', 'Solicitud de curso o capacitación en herramientas', 'low'),
    ('TI-DES', 'Desarrollo/Mejora de sistema', 'Solicitud de nueva funcionalidad, mejora de sistema', 'low'),
    ('TI-OTR', 'Otro (TI)', 'Otro tipo de solicitud de TI no listada', 'medium')
) AS s(code, name, description, priority)
WHERE c.code = 'TI'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert RH Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('RH-VAC', 'Solicitud de vacaciones', 'Días de vacaciones', 'medium'),
    ('RH-PER', 'Permiso con/sin goce', 'Permiso por asunto personal', 'medium'),
    ('RH-INC', 'Incapacidad', 'Registro de incapacidad médica', 'high'),
    ('RH-NOM', 'Aclaración de nómina', 'Duda o error en pago', 'high'),
    ('RH-CST', 'Constancia laboral', 'Solicitud de constancia', 'low'),
    ('RH-CRD', 'Credencial institucional', 'Nueva credencial o reposición', 'low'),
    ('RH-CAP', 'Capacitación', 'Solicitud de curso o capacitación', 'low'),
    ('RH-EVA', 'Evaluación de desempeño', 'Proceso de evaluación', 'medium'),
    ('RH-ALT', 'Alta de empleado', 'Nuevo ingreso', 'high'),
    ('RH-BAJ', 'Baja de empleado', 'Renuncia, despido, jubilación', 'high'),
    ('RH-CAM', 'Cambio de adscripción', 'Cambio de área o puesto', 'medium'),
    ('RH-HRS', 'Horario/Asistencia', 'Ajuste de checadas, horario', 'medium'),
    ('RH-PRE', 'Préstamo personal', 'Solicitud de préstamo', 'low'),
    ('RH-SEG', 'Seguro médico', 'Altas, bajas, aclaraciones IMSS', 'medium'),
    ('RH-UNI', 'Uniformes', 'Solicitud de uniformes', 'low')
) AS s(code, name, description, priority)
WHERE c.code = 'RH'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert MNT Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('MNT-ELE', 'Falla eléctrica', 'Apagones, contactos, lámparas', 'high'),
    ('MNT-PLO', 'Plomería', 'Fugas, baños, lavabos', 'high'),
    ('MNT-CLI', 'Clima/Aire acondicionado', 'Falla o mantenimiento de A/C', 'medium'),
    ('MNT-CER', 'Cerrajería', 'Chapas, llaves, puertas', 'medium'),
    ('MNT-PIN', 'Pintura', 'Retoques, pintura de áreas', 'low'),
    ('MNT-LIM', 'Limpieza especial', 'Limpieza profunda, fumigación', 'low'),
    ('MNT-MOB', 'Mobiliario', 'Sillas, escritorios, archiveros', 'low'),
    ('MNT-JAR', 'Jardinería', 'Áreas verdes, poda', 'low'),
    ('MNT-SEÑ', 'Señalización', 'Letreros, señales de seguridad', 'low'),
    ('MNT-VID', 'Vidrios/Ventanas', 'Reparación de cristales', 'medium'),
    ('MNT-TEC', 'Techos/Goteras', 'Filtraciones, impermeabilización', 'high'),
    ('MNT-EST', 'Estacionamiento', 'Baches, pintura, señalización', 'low')
) AS s(code, name, description, priority)
WHERE c.code = 'MNT'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert VEH Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('VEH-SOL', 'Solicitud de vehículo', 'Reservación para comisión', 'medium'),
    ('VEH-FAL', 'Falla mecánica', 'Reporte de falla en unidad', 'high'),
    ('VEH-COM', 'Combustible', 'Solicitud de vales o carga', 'medium'),
    ('VEH-MNT', 'Mantenimiento', 'Servicio, llantas, afinación', 'medium'),
    ('VEH-ACC', 'Accidente/Siniestro', 'Reporte de accidente', 'urgent'),
    ('VEH-GPS', 'Falla GPS/Rastreo', 'Problema con sistema de rastreo', 'low'),
    ('VEH-DOC', 'Documentación', 'Tarjeta de circulación, verificación', 'medium'),
    ('VEH-INF', 'Infracción', 'Reporte de multa', 'medium')
) AS s(code, name, description, priority)
WHERE c.code = 'VEH'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert ALM Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('ALM-PAP', 'Papelería', 'Hojas, folders, plumas, etc.', 'low'),
    ('ALM-TON', 'Tóner/Cartuchos', 'Consumibles de impresión', 'medium'),
    ('ALM-LIM', 'Artículos de limpieza', 'Jabón, papel, químicos', 'low'),
    ('ALM-HER', 'Herramientas', 'Solicitud de herramientas', 'medium'),
    ('ALM-EQS', 'Equipo de seguridad', 'EPP, cascos, chalecos', 'high'),
    ('ALM-MOB', 'Mobiliario', 'Solicitud de muebles', 'low'),
    ('ALM-MAT', 'Material de construcción', 'Cemento, tubería, conexiones', 'medium'),
    ('ALM-DEV', 'Devolución de material', 'Regreso de material no usado', 'low')
) AS s(code, name, description, priority)
WHERE c.code = 'ALM'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert ADM Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('ADM-OFI', 'Oficio/Memorándum', 'Solicitud de elaboración', 'medium'),
    ('ADM-FIR', 'Firma de documentos', 'Solicitud de firma a dirección', 'medium'),
    ('ADM-ARC', 'Archivo', 'Solicitud de expediente o documento', 'low'),
    ('ADM-COP', 'Copias certificadas', 'Solicitud de copias oficiales', 'low'),
    ('ADM-VIA', 'Viáticos', 'Solicitud de viáticos', 'medium'),
    ('ADM-CAJ', 'Caja chica', 'Reembolso o solicitud', 'medium'),
    ('ADM-FAC', 'Facturación interna', 'Solicitud de factura', 'medium'),
    ('ADM-COM', 'Compras', 'Requisición de compra', 'medium'),
    ('ADM-CON', 'Contratos/Convenios', 'Elaboración o revisión', 'medium'),
    ('ADM-SEG', 'Póliza de seguro', 'Trámites de seguros institucionales', 'low')
) AS s(code, name, description, priority)
WHERE c.code = 'ADM'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert COM Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('COM-DIS', 'Diseño gráfico', 'Carteles, lonas, presentaciones', 'medium'),
    ('COM-FOT', 'Fotografía/Video', 'Cobertura de evento', 'medium'),
    ('COM-RED', 'Redes sociales', 'Publicación en redes', 'medium'),
    ('COM-BOL', 'Boletín de prensa', 'Comunicado oficial', 'high'),
    ('COM-EVT', 'Evento institucional', 'Apoyo logístico para evento', 'medium'),
    ('COM-WEB', 'Contenido web', 'Actualización de portal', 'low'),
    ('COM-INT', 'Comunicación interna', 'Circular, aviso interno', 'medium')
) AS s(code, name, description, priority)
WHERE c.code = 'COM'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert JUR Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('JUR-CON', 'Consulta legal', 'Asesoría jurídica', 'medium'),
    ('JUR-REV', 'Revisión de contrato', 'Validación de documento legal', 'medium'),
    ('JUR-DEM', 'Demanda/Litigio', 'Seguimiento a proceso legal', 'high'),
    ('JUR-NOT', 'Notificación legal', 'Elaboración de notificación', 'medium'),
    ('JUR-POD', 'Poder notarial', 'Trámite de poder', 'medium'),
    ('JUR-QUE', 'Queja ciudadana formal', 'Atención a queja que requiere jurídico', 'high')
) AS s(code, name, description, priority)
WHERE c.code = 'JUR'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Insert SEG Subcategories
-- ============================================

INSERT INTO internal_ticket_subcategories (category_id, code, name, description, default_priority)
SELECT c.id, s.code, s.name, s.description, s.priority
FROM internal_ticket_categories c
CROSS JOIN (VALUES
    ('SEG-ACC', 'Control de acceso', 'Gafete, registro de visitante', 'medium'),
    ('SEG-CAM', 'Cámaras/CCTV', 'Revisión de grabaciones, falla', 'medium'),
    ('SEG-INC', 'Incidente de seguridad', 'Robo, vandalismo, amenaza', 'urgent'),
    ('SEG-VIG', 'Vigilancia especial', 'Solicitud de rondín o custodia', 'medium'),
    ('SEG-EME', 'Emergencia', 'Incendio, sismo, evacuación', 'urgent'),
    ('SEG-INV', 'Investigación interna', 'Seguimiento a incidente', 'high')
) AS s(code, name, description, priority)
WHERE c.code = 'SEG'
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Update timestamp trigger
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_internal_tickets_updated_at ON internal_tickets;
CREATE TRIGGER update_internal_tickets_updated_at
    BEFORE UPDATE ON internal_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
