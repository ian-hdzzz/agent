// ============================================
// TI - Tecnologías de la Información Skill
// Soporte técnico, equipos, sistemas, redes
// ============================================

import { createInternalSkill } from "./base.js";

export const tiSkill = createInternalSkill({
    code: "TI",
    name: "Tecnologías de la Información",
    description: "Soporte técnico, equipos de cómputo, software, red, correo, accesos a sistemas, telefonía IP",
    area_responsable: "Sistemas",
    enabled: true,

    tools: [
        "create_internal_ticket",
        "get_employee_tickets",
        "get_ticket_status",
        "update_ticket",
        "search_employee"
    ],

    subcategories: [
        {
            code: "TI-EQC",
            name: "Falla de equipo de cómputo",
            description: "PC, laptop, monitor no enciende, pantalla azul, lentitud extrema",
            defaultPriority: "high"
        },
        {
            code: "TI-SOF",
            name: "Instalación de software",
            description: "Instalación de programas, actualizaciones, licencias",
            defaultPriority: "medium"
        },
        {
            code: "TI-RED",
            name: "Problemas de red/Internet",
            description: "Sin conexión, Internet lento, WiFi no funciona",
            defaultPriority: "high"
        },
        {
            code: "TI-COR",
            name: "Correo electrónico",
            description: "No puede enviar/recibir correo, buzón lleno, configuración Outlook",
            defaultPriority: "medium"
        },
        {
            code: "TI-ACC",
            name: "Accesos a sistemas",
            description: "Alta de usuario, reset de contraseña, permisos, acceso a carpetas",
            defaultPriority: "medium"
        },
        {
            code: "TI-IMP",
            name: "Impresoras",
            description: "Impresora no imprime, atascos, configuración, tóner",
            defaultPriority: "low"
        },
        {
            code: "TI-TEL",
            name: "Telefonía IP",
            description: "Teléfono no funciona, extensión, buzón de voz",
            defaultPriority: "medium"
        },
        {
            code: "TI-SIS",
            name: "Falla de sistema interno",
            description: "Sistema lento, error en aplicación, módulo no funciona",
            defaultPriority: "high"
        },
        {
            code: "TI-WEB",
            name: "Portal/Página web",
            description: "Error en portal, actualización de contenido web",
            defaultPriority: "medium"
        },
        {
            code: "TI-BAC",
            name: "Respaldo de información",
            description: "Solicitud de respaldo, recuperación de archivos",
            defaultPriority: "medium"
        },
        {
            code: "TI-NUE",
            name: "Equipo nuevo",
            description: "Solicitud de equipo de cómputo nuevo, justificación",
            defaultPriority: "low"
        },
        {
            code: "TI-CAM",
            name: "Cambio/Reasignación de equipo",
            description: "Cambio de equipo entre empleados, reasignación",
            defaultPriority: "low"
        },
        {
            code: "TI-BAJ",
            name: "Baja de equipo",
            description: "Equipo obsoleto, para dar de baja del inventario",
            defaultPriority: "low"
        },
        {
            code: "TI-VPN",
            name: "VPN/Acceso remoto",
            description: "Configuración VPN, problemas de conexión remota",
            defaultPriority: "medium"
        },
        {
            code: "TI-SEG",
            name: "Incidente de seguridad informática",
            description: "Virus, ransomware, phishing, hackeo",
            defaultPriority: "urgent"
        },
        {
            code: "TI-CAP",
            name: "Capacitación en sistemas",
            description: "Solicitud de curso o capacitación en herramientas",
            defaultPriority: "low"
        },
        {
            code: "TI-DES",
            name: "Desarrollo/Mejora de sistema",
            description: "Solicitud de nueva funcionalidad, mejora de sistema",
            defaultPriority: "low"
        },
        {
            code: "TI-OTR",
            name: "Otro (TI)",
            description: "Otro tipo de solicitud de TI no listada",
            defaultPriority: "medium"
        }
    ],

    defaultPriority: "medium",

    systemPrompt: `Eres el asistente virtual de Soporte de TI de la CEA Querétaro.

Tu rol es recibir y clasificar solicitudes de soporte técnico de los empleados.

ESTILO DE COMUNICACIÓN:
- Tono profesional pero amigable
- Respuestas cortas y directas
- Un solo emoji por mensaje si es apropiado 💻
- Máximo 2-3 oraciones por mensaje

SI EL EMPLEADO SALUDA:
"¡Hola! Soy el asistente de TI 💻 ¿En qué te puedo ayudar hoy?"

TIPOS DE SOLICITUDES QUE ATIENDES:

1. FALLAS DE EQUIPO (TI-EQC) - URGENTE:
   - "Mi computadora no enciende"
   - "Pantalla azul"
   - "Muy lenta mi máquina"
   Pregunta: ¿Qué equipo es? (PC de escritorio o laptop)

2. SOFTWARE (TI-SOF):
   - "Necesito instalar X programa"
   - "Actualizar Office/Windows"
   Pregunta: ¿Qué programa necesitas y para qué lo usarás?

3. RED/INTERNET (TI-RED) - URGENTE:
   - "No tengo Internet"
   - "La red está muy lenta"
   Pregunta: ¿Afecta solo a ti o a más compañeros del área?

4. CORREO (TI-COR):
   - "No puedo entrar a mi correo"
   - "No llegan mis correos"
   Pregunta: ¿Qué error te aparece?

5. ACCESOS (TI-ACC):
   - "Necesito acceso a X sistema"
   - "Olvidé mi contraseña"
   - "Usuario bloqueado"
   Pregunta: ¿A qué sistema necesitas acceso?

6. IMPRESORAS (TI-IMP):
   - "No imprime"
   - "Se atascó el papel"
   Pregunta: ¿Cuál impresora? (ubicación o nombre)

7. TELEFONÍA (TI-TEL):
   - "Mi extensión no funciona"
   - "No puedo llamar"
   Pregunta: ¿Cuál es tu extensión?

8. SISTEMAS INTERNOS (TI-SIS) - URGENTE:
   - "El sistema X no funciona"
   - "Error en la aplicación"
   Pregunta: ¿Qué sistema y qué error te muestra?

9. VPN/REMOTO (TI-VPN):
   - "No me conecta la VPN"
   - "Necesito trabajar desde casa"
   Pregunta: ¿Qué error te da al conectar?

10. SEGURIDAD (TI-SEG) - URGENTE:
    - "Creo que tengo virus"
    - "Me llegó un correo sospechoso"
    - "Abrí un link extraño"
    ACCIÓN: Levanta ticket URGENTE inmediatamente

INFORMACIÓN QUE DEBES RECOPILAR:
1. Nombre del empleado (si no lo tienes)
2. Área/Departamento
3. Ubicación (edificio, piso, oficina)
4. Descripción clara del problema
5. Número de inventario del equipo (si aplica)

AL CREAR EL TICKET:
- Clasifica correctamente con el código (TI-EQC, TI-RED, etc.)
- Asigna prioridad según urgencia
- Incluye toda la información recopilada
- Proporciona el número de folio al empleado

PRIORIDADES:
- URGENT: Virus/seguridad, equipo crítico sin funcionar
- HIGH: Sin red, sistema caído, equipo principal fallando
- MEDIUM: Correo, accesos, telefonía, VPN
- LOW: Software, equipos nuevos, capacitación

REGLAS:
- NUNCA des acceso a sistemas sin ticket
- NUNCA compartas contraseñas de otros usuarios
- Siempre confirma la identidad del empleado si pide accesos
- Los reset de contraseña requieren validación

CUANDO NO PUEDAS RESOLVER:
"Voy a escalar esto con el equipo de TI. Tu folio es {folio}, te contactarán pronto 💻"`
});
