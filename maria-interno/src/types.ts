// ============================================
// Maria Interno - Type Definitions
// Sistema de Tickets Internos para Empleados
// ============================================

import { z } from "zod";

// ============================================
// Categorías de Tickets Internos
// ============================================

export type CategoryCode =
    | "TI"   // Tecnologías de la Información
    | "RH"   // Recursos Humanos
    | "MNT"  // Mantenimiento de Instalaciones
    | "VEH"  // Vehículos y Transporte
    | "ALM"  // Almacén y Suministros
    | "ADM"  // Administrativo
    | "COM"  // Comunicación Social
    | "JUR"  // Jurídico
    | "SEG"; // Seguridad Institucional

export const CategorySchema = z.enum(["TI", "RH", "MNT", "VEH", "ALM", "ADM", "COM", "JUR", "SEG"]);

export interface CategoryDefinition {
    code: CategoryCode;
    name: string;
    description: string;
    area_responsable: string;
    subcategorias_count: number;
}

export const INTERNAL_CATEGORIES: Record<CategoryCode, CategoryDefinition> = {
    TI: {
        code: "TI",
        name: "Tecnologías de la Información",
        description: "Soporte técnico, equipos, sistemas, correo, redes y telefonía",
        area_responsable: "Sistemas",
        subcategorias_count: 18
    },
    RH: {
        code: "RH",
        name: "Recursos Humanos",
        description: "Solicitudes y trámites de personal",
        area_responsable: "Capital Humano",
        subcategorias_count: 15
    },
    MNT: {
        code: "MNT",
        name: "Mantenimiento de Instalaciones",
        description: "Servicios de mantenimiento a oficinas y edificios",
        area_responsable: "Servicios Generales",
        subcategorias_count: 12
    },
    VEH: {
        code: "VEH",
        name: "Vehículos y Transporte",
        description: "Solicitudes relacionadas con la flotilla vehicular",
        area_responsable: "Transporte",
        subcategorias_count: 8
    },
    ALM: {
        code: "ALM",
        name: "Almacén y Suministros",
        description: "Solicitudes de materiales e insumos",
        area_responsable: "Almacén",
        subcategorias_count: 8
    },
    ADM: {
        code: "ADM",
        name: "Administrativo",
        description: "Trámites administrativos internos",
        area_responsable: "Administración",
        subcategorias_count: 10
    },
    COM: {
        code: "COM",
        name: "Comunicación Social",
        description: "Solicitudes al área de comunicación",
        area_responsable: "Comunicación",
        subcategorias_count: 7
    },
    JUR: {
        code: "JUR",
        name: "Jurídico",
        description: "Solicitudes al área legal",
        area_responsable: "Jurídico",
        subcategorias_count: 6
    },
    SEG: {
        code: "SEG",
        name: "Seguridad Institucional",
        description: "Solicitudes de seguridad y vigilancia",
        area_responsable: "Seguridad",
        subcategorias_count: 6
    }
};

// ============================================
// Subcategorías por Área
// ============================================

// TI - Tecnologías de la Información (18 subcategorías)
export type TISubcategoryCode =
    | "TI-EQC"   // Falla de equipo de cómputo
    | "TI-SOF"   // Instalación de software
    | "TI-RED"   // Problemas de red/Internet
    | "TI-COR"   // Correo electrónico
    | "TI-ACC"   // Accesos a sistemas
    | "TI-IMP"   // Impresoras
    | "TI-TEL"   // Telefonía IP
    | "TI-SIS"   // Falla de sistema interno
    | "TI-WEB"   // Portal/Página web
    | "TI-BAC"   // Respaldo de información
    | "TI-NUE"   // Equipo nuevo
    | "TI-CAM"   // Cambio/Reasignación de equipo
    | "TI-BAJ"   // Baja de equipo
    | "TI-VPN"   // VPN/Acceso remoto
    | "TI-SEG"   // Incidente de seguridad informática
    | "TI-CAP"   // Capacitación en sistemas
    | "TI-DES"   // Desarrollo/Mejora de sistema
    | "TI-OTR";  // Otro (TI)

// RH - Recursos Humanos (15 subcategorías)
export type RHSubcategoryCode =
    | "RH-VAC"   // Solicitud de vacaciones
    | "RH-PER"   // Permiso con/sin goce
    | "RH-INC"   // Incapacidad
    | "RH-NOM"   // Aclaración de nómina
    | "RH-CST"   // Constancia laboral
    | "RH-CRD"   // Credencial institucional
    | "RH-CAP"   // Capacitación
    | "RH-EVA"   // Evaluación de desempeño
    | "RH-ALT"   // Alta de empleado
    | "RH-BAJ"   // Baja de empleado
    | "RH-CAM"   // Cambio de adscripción
    | "RH-HRS"   // Horario/Asistencia
    | "RH-PRE"   // Préstamo personal
    | "RH-SEG"   // Seguro médico
    | "RH-UNI";  // Uniformes

// MNT - Mantenimiento (12 subcategorías)
export type MNTSubcategoryCode =
    | "MNT-ELE"  // Falla eléctrica
    | "MNT-PLO"  // Plomería
    | "MNT-CLI"  // Clima/Aire acondicionado
    | "MNT-CER"  // Cerrajería
    | "MNT-PIN"  // Pintura
    | "MNT-LIM"  // Limpieza especial
    | "MNT-MOB"  // Mobiliario
    | "MNT-JAR"  // Jardinería
    | "MNT-SEÑ"  // Señalización
    | "MNT-VID"  // Vidrios/Ventanas
    | "MNT-TEC"  // Techos/Goteras
    | "MNT-EST"; // Estacionamiento

// VEH - Vehículos (8 subcategorías)
export type VEHSubcategoryCode =
    | "VEH-SOL"  // Solicitud de vehículo
    | "VEH-FAL"  // Falla mecánica
    | "VEH-COM"  // Combustible
    | "VEH-MNT"  // Mantenimiento
    | "VEH-ACC"  // Accidente/Siniestro
    | "VEH-GPS"  // Falla GPS/Rastreo
    | "VEH-DOC"  // Documentación
    | "VEH-INF"; // Infracción

// ALM - Almacén (8 subcategorías)
export type ALMSubcategoryCode =
    | "ALM-PAP"  // Papelería
    | "ALM-TON"  // Tóner/Cartuchos
    | "ALM-LIM"  // Artículos de limpieza
    | "ALM-HER"  // Herramientas
    | "ALM-EQS"  // Equipo de seguridad
    | "ALM-MOB"  // Mobiliario
    | "ALM-MAT"  // Material de construcción
    | "ALM-DEV"; // Devolución de material

// ADM - Administrativo (10 subcategorías)
export type ADMSubcategoryCode =
    | "ADM-OFI"  // Oficio/Memorándum
    | "ADM-FIR"  // Firma de documentos
    | "ADM-ARC"  // Archivo
    | "ADM-COP"  // Copias certificadas
    | "ADM-VIA"  // Viáticos
    | "ADM-CAJ"  // Caja chica
    | "ADM-FAC"  // Facturación interna
    | "ADM-COM"  // Compras
    | "ADM-CON"  // Contratos/Convenios
    | "ADM-SEG"; // Póliza de seguro

// COM - Comunicación Social (7 subcategorías)
export type COMSubcategoryCode =
    | "COM-DIS"  // Diseño gráfico
    | "COM-FOT"  // Fotografía/Video
    | "COM-RED"  // Redes sociales
    | "COM-BOL"  // Boletín de prensa
    | "COM-EVT"  // Evento institucional
    | "COM-WEB"  // Contenido web
    | "COM-INT"; // Comunicación interna

// JUR - Jurídico (6 subcategorías)
export type JURSubcategoryCode =
    | "JUR-CON"  // Consulta legal
    | "JUR-REV"  // Revisión de contrato
    | "JUR-DEM"  // Demanda/Litigio
    | "JUR-NOT"  // Notificación legal
    | "JUR-POD"  // Poder notarial
    | "JUR-QUE"; // Queja ciudadana formal

// SEG - Seguridad (6 subcategorías)
export type SEGSubcategoryCode =
    | "SEG-ACC"  // Control de acceso
    | "SEG-CAM"  // Cámaras/CCTV
    | "SEG-INC"  // Incidente de seguridad
    | "SEG-VIG"  // Vigilancia especial
    | "SEG-EME"  // Emergencia
    | "SEG-INV"; // Investigación interna

// Union type for all subcategories
export type SubcategoryCode =
    | TISubcategoryCode
    | RHSubcategoryCode
    | MNTSubcategoryCode
    | VEHSubcategoryCode
    | ALMSubcategoryCode
    | ADMSubcategoryCode
    | COMSubcategoryCode
    | JURSubcategoryCode
    | SEGSubcategoryCode;

// ============================================
// Ticket Types
// ============================================

export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketStatus = "open" | "in_progress" | "escalated" | "waiting_employee" | "waiting_internal" | "resolved" | "closed" | "cancelled";

// ============================================
// Employee Types
// ============================================

export interface Employee {
    id: string;
    numero_empleado: string;
    nombre: string;
    email: string;
    area: string;
    puesto: string;
    extension?: string;
    ubicacion?: string;
}

// ============================================
// Internal Ticket Types
// ============================================

export interface CreateInternalTicketInput {
    category_code: CategoryCode;
    subcategory_code?: SubcategoryCode;
    titulo: string;
    descripcion: string;
    employee_id?: string;
    employee_name?: string;
    employee_email?: string;
    area_solicitante?: string;
    ubicacion?: string;
    priority?: TicketPriority;
    channel?: string;
    metadata?: Record<string, unknown>;
}

export interface CreateInternalTicketResult {
    success: boolean;
    folio?: string;
    ticketId?: string;
    message?: string;
    warning?: string;
    error?: string;
}

// ============================================
// Workflow Types
// ============================================

export interface InternalWorkflowInput {
    input_as_text: string;
    conversationId?: string;
    metadata?: {
        employee_id?: string;
        employee_name?: string;
        employee_email?: string;
        employee_phone?: string;
        custom_attributes?: Record<string, unknown>;
        area?: string;
        channel?: string;
    };
    // Chatwoot context for handoff
    chatwootAccountId?: number;
    chatwootConversationId?: number;
}

export interface InternalWorkflowOutput {
    output_text: string;
    category?: CategoryCode;
    subcategory?: SubcategoryCode;
    toolsUsed?: string[];
    error?: string;
}

// ============================================
// Skill Definition Types
// ============================================

export interface InternalSkill {
    code: CategoryCode;
    name: string;
    description: string;
    systemPrompt: string;
    tools: string[];
    subcategories: Array<{
        code: SubcategoryCode;
        name: string;
        description: string;
        defaultPriority?: TicketPriority;
    }>;
    area_responsable: string;
    enabled: boolean;
}

// ============================================
// Classification Schema
// ============================================

export const InternalClassificationSchema = z.object({
    category: CategorySchema,
    subcategory: z.string().nullable().describe("Subcategory code if determined"),
    confidence: z.number().min(0).max(1).nullable().describe("Confidence score"),
    extractedEmployeeId: z.string().nullable().describe("Extracted employee ID if found")
});

export type InternalClassification = z.infer<typeof InternalClassificationSchema>;

// ============================================
// Chatwoot Types (same as external)
// ============================================

export interface ChatwootSender {
    id: number;
    name: string;
    avatar: string | null;
    type: "contact" | "user" | "agent_bot";
    email?: string | null;
    phone_number?: string;
    identifier?: string;
    custom_attributes?: Record<string, unknown>;
    additional_attributes?: Record<string, unknown>;
}

export interface ChatwootInbox {
    id: number;
    name: string;
}

export interface ChatwootConversation {
    id: number;
    inbox_id: number;
    status: "open" | "resolved" | "pending" | "snoozed";
    agent_last_seen_at: string | null;
    contact_last_seen_at: string | null;
    timestamp: string;
    additional_attributes: Record<string, unknown>;
    channel: string;
}

export interface ChatwootAccount {
    id: number;
    name: string;
}

export interface ChatwootWebhookPayload {
    event: "message_created" | "message_updated" | "conversation_created" |
           "conversation_updated" | "conversation_status_changed" |
           "webwidget_triggered" | "conversation_typing_on" | "conversation_typing_off";
    id: number;
    content: string | null;
    created_at: string;
    message_type: "incoming" | "outgoing" | "activity" | "template";
    content_type: string;
    content_attributes: Record<string, unknown>;
    source_id: string | null;
    sender: ChatwootSender;
    inbox: ChatwootInbox;
    conversation: ChatwootConversation;
    account: ChatwootAccount;
}
