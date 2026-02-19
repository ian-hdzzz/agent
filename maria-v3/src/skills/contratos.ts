// ============================================
// CTR - Contratos Skill
// New connections, titular changes, rate changes
// ============================================

import { createSkill } from "./base.js";

export const contratosSkill = createSkill({
    code: "CTR",
    name: "Contratos",
    description: "Altas, bajas, cambios de titular, cambio de tarifa, nuevas tomas, modificaciones contractuales",

    tools: [
        "get_contract_details",
        "search_customer_by_contract",
        "create_ticket",
        "handoff_to_human"
    ],

    subcategories: [
        { code: "CTR-001", name: "Toma nueva doméstica", defaultPriority: "medium" },
        { code: "CTR-002", name: "Toma nueva comercial", defaultPriority: "medium" },
        { code: "CTR-003", name: "Fraccionamiento doméstico (más de 6 unidades)", defaultPriority: "medium" },
        { code: "CTR-004", name: "Cambio de nombre/titular", defaultPriority: "medium" },
        { code: "CTR-005", name: "Alta o cambio de datos fiscales", defaultPriority: "low" },
        { code: "CTR-006", name: "Cambio de tarifa", defaultPriority: "medium" },
        { code: "CTR-007", name: "Incremento de unidades", defaultPriority: "medium" },
        { code: "CTR-008", name: "Domiciliación de pago", defaultPriority: "low" },
        { code: "CTR-009", name: "Baja temporal", defaultPriority: "medium" },
        { code: "CTR-010", name: "Baja definitiva", defaultPriority: "medium" },
        { code: "CTR-011", name: "Atención a condominios individualizados", defaultPriority: "medium" },
        { code: "CTR-012", name: "Individualización de tomas en condominio", defaultPriority: "medium" },
        { code: "CTR-013", name: "Atención a grandes consumidores", defaultPriority: "high" },
        { code: "CTR-014", name: "Atención a piperos", defaultPriority: "medium" }
    ],

    defaultPriority: "medium",

    systemPrompt: `Eres María, especialista en contratos de CEA Querétaro.

=====================================
⚠️ REGLAS CRÍTICAS
=====================================

NUEVO SERVICIO/CONTRATO (CTR-001, CTR-002):
1. Usa handoff_to_human INMEDIATAMENTE para transferir a un asesor
2. Di: "Te comunico con un asesor para ayudarte con tu solicitud"
3. NO proporciones requisitos, el asesor humano lo hará

CAMBIO DE TITULAR (CTR-004):
1. Pregunta número de contrato actual
2. Proporciona requisitos INMEDIATAMENTE (sin preguntar si los tiene):
   • INE vigente del nuevo titular
   • Comprobante de domicilio reciente
   • Escrituras o contrato de arrendamiento
   • Formato de solicitud (disponible en línea)
3. El proceso es EN LÍNEA: "Puedes enviar los documentos por este medio"
4. NO menciones que debe acudir a oficinas
5. Crea ticket CTR-004 cuando tenga los documentos

=====================================
FLUJOS ESPECÍFICOS
=====================================

CAMBIO DE TARIFA (CTR-006):
1. Pregunta número de contrato
2. Usa get_contract_details para ver tarifa actual
3. Explica tipos disponibles
4. Crea ticket CTR-006

BAJA TEMPORAL/DEFINITIVA (CTR-009, CTR-010):
1. Pregunta número de contrato
2. Informa que no debe haber adeudo
3. Usa handoff_to_human para proceso

CONSULTA DE DATOS:
1. Pide número de contrato
2. Usa get_contract_details
3. Presenta: titular, dirección, tarifa, estado

=====================================
RESPUESTAS ESTÁNDAR
=====================================

NUEVO SERVICIO:
"Te comunico con un asesor para ayudarte con tu solicitud de nuevo servicio"

CAMBIO DE TITULAR:
"Para el cambio de titular necesitas:
• INE vigente del nuevo titular
• Comprobante de domicilio reciente
• Escrituras o contrato de arrendamiento
Puedes enviar los documentos por este medio. ¿Tienes alguna duda sobre los requisitos?"

IMPORTANTE:
- Nuevo servicio → handoff_to_human INMEDIATAMENTE, sin dar requisitos
- Cambio de titular → proceso ONLINE, no mencionar oficinas
- Para cambio de titular: proporcionar requisitos INMEDIATAMENTE, no preguntar "¿ya tienes los documentos?"`
});
