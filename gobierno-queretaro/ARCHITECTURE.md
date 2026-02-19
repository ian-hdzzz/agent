# Gobierno Queretaro - Intelligent Agent System Architecture

## Overview

This document describes the architecture for transforming the existing "dumb-bot" menu-driven system into an intelligent multi-agent orchestrated system using LangGraph and Claude.

## Service Categories (13 Agents)

| Code | Agent ID | Service | Organization |
|------|----------|---------|--------------|
| ATC | citizen-attention | Atencion Ciudadana | General |
| TRA | transport-ameq | Transporte Publico | AMEQ |
| CEA | water-cea | Servicios de Agua | CEA |
| EDU | education-usebeq | Educacion Basica | USEBEQ |
| VEH | vehicles | Tramites Vehiculares | Sec. Finanzas |
| PSI | psychology-sejuve | Atencion Psicologica | SEJUVE |
| IQM | women-iqm | Atencion a Mujeres | IQM |
| CUL | culture | Cultura y RPP | Sec. Cultura |
| RPP | registry-rpp | Registro Publico | RPP |
| LAB | labor-cclq | Conciliacion Laboral | CCLQ |
| VIV | housing-iveq | Vivienda | IVEQ |
| APP | appqro | Soporte APPQRO | Digital |
| SOC | social-sedesoq | Programas Sociales | SEDESOQ |

## Classification Keywords

### 1. ATC - Atencion Ciudadana
```
Keywords: contacto, contactanos, atencion, quejas, sugerencias, informacion general
Subcategories: ATC-CON-001 (Contacto general)
```

### 2. TRA - Transporte AMEQ
```
Keywords: transporte, autobus, camion, ruta, qrobus, tarjeta, pasaje, tarifa, horario, parada, ameq, estudiante credencial, adulto mayor inapam, discapacidad, prepago, saldo tarjeta
Subcategories:
- TRA-INF-001: Informacion general transporte
- TRA-TAR-001: Obtener/renovar tarjeta preferente
- TRA-EST-001: Tarjeta estudiante
- TRA-ADM-001: Tarjeta adulto mayor
- TRA-DIS-001: Tarjeta discapacidad
- TRA-NIN-001: Tarjeta nino 3-6 anos
- TRA-UNI-001: Tarifa UNIDOS ($2)
- TRA-SAL-001: Consulta saldo tarjeta
- TRA-HIS-001: Historial de tarjeta
- TRA-RUT-001: Consulta de rutas
- TRA-MAP-001: Mapa de rutas
- TRA-PER-001: Permiso/concesion transporte
- TRA-TIO-001: Obtener/renovar TIO
- TRA-VEH-001: Tramites de vehiculo transporte
- TRA-EVA-001: Evaluar/sugerir servicio
```

### 3. CEA - Servicios de Agua
```
Keywords: agua, cea, recibo, pago, contrato, lectura, fuga, drenaje, aclaracion
Subcategories:
- CEA-ACL-001: Aclaraciones
- CEA-ACT-001: Actualizar caso
- CEA-CTR-001: Contratacion/cambio nombre
- CEA-ASE-001: Hablar con asesor
- CEA-PAG-001: Pagar recibo
- CEA-LEC-001: Reportar lectura
- CEA-REP-001: Reportes y fugas
- CEA-REV-001: Revision de recibo
- CEA-DIG-001: Recibo digital
```

### 4. EDU - Educacion USEBEQ
```
Keywords: escuela, preinscripcion, inscripcion, vinculacion, curp, estudiante, usebeq, educacion, aspirante
Subcategories:
- EDU-VIN-001: Verifica vinculacion
- EDU-PRE-001: Preinscripciones
- EDU-ASE-001: Asesoria educativa
```

### 5. VEH - Tramites Vehiculares
```
Keywords: tenencia, placa, vehiculo, carro, auto, comprobante, pago vehicular, oficina recaudadora, sustitucion placa
Subcategories:
- VEH-TEN-001: Pago tenencia
- VEH-OFI-001: Oficinas recaudadoras
- VEH-CON-001: Consulta/pago portal
- VEH-COM-001: Descarga comprobante
- VEH-FAQ-001: Preguntas frecuentes
- VEH-SUS-001: Sustitucion de placa
- VEH-INF-001: Informacion tenencia
- VEH-DES-001: Placas desgastadas
```

### 6. PSI - Psicologia SEJUVE
```
Keywords: psicologico, psicologo, emocional, salud mental, sejuve, tranquilidad, apoyo emocional
Subcategories:
- PSI-ATE-001: Atencion psicologica
```

### 7. IQM - Atencion a Mujeres
```
Keywords: mujer, violencia, iqm, apoyo, legal, psicologica, tel mujer
Subcategories:
- IQM-CON-001: Contacto IQM
- IQM-CEN-001: Centros de atencion
- IQM-VIO-001: Pasos ante violencia
- IQM-UBI-001: Ubicacion IQM
```

### 8. CUL - Cultura
```
Keywords: cultura, museo, centro cultural, galeria, arte, evento cultural, cartelera
Subcategories:
- CUL-CEN-001: Centros culturales
- CUL-CAR-001: Cartelera cultural
- CUL-PRO-001: Programas culturales
- CUL-CON-001: Contacto cultura
```

### 9. RPP - Registro Publico de la Propiedad
```
Keywords: registro publico, rpp, certificado, gravamen, propiedad, escritura, inmueble, hipoteca, testamento
Subcategories:
- RPP-CON-001: Consulta inmobiliaria
- RPP-REG-001: Registro acceso RPP
- RPP-REC-001: Recuperar contrasena
- RPP-CER-001: Certificados/copias
- RPP-GRA-001: Certificado gravamen
- RPP-INS-001: Certificado inscripcion
- RPP-PRO-001: Certificado propiedad
- RPP-UNI-001: Certificado unica propiedad
- RPP-NOP-001: Certificado no propiedad
- RPP-HIS-001: Historial registral
- RPP-BUS-001: Busqueda antecedentes
- RPP-HIP-001: Cancelacion hipoteca
- RPP-CAD-001: Cancelacion caducidad
- RPP-DEM-001: Demanda/embargo
- RPP-TES-001: Validacion testamento
- RPP-ALB-001: Nombramiento albacea
- RPP-ACL-001: Aclaraciones
- RPP-COS-001: Costos
- RPP-HOR-001: Horarios
- RPP-UBI-001: Ubicaciones
- RPP-ALE-001: Alerta registral
- RPP-SEG-001: Seguimiento tramite
```

### 10. LAB - Conciliacion Laboral CCLQ
```
Keywords: laboral, trabajo, demanda laboral, conciliacion, despido, cclq, convenio, colectivo
Subcategories:
- LAB-ASE-001: Asesoria juridica
- LAB-PRO-001: Proceso conciliacion
- LAB-CON-001: Realizar convenio
- LAB-COL-001: Asunto colectivo
- LAB-INF-001: Informacion contacto
- LAB-ANT-001: Asunto anterior nov 2021
```

### 11. VIV - Vivienda IVEQ
```
Keywords: vivienda, iveq, escriturar, cesion derechos, constancia no adeudo, planos, autoproduccion
Subcategories:
- VIV-CNA-001: Constancia no adeudo
- VIV-PLA-001: Expedicion copias/planos
- VIV-CES-001: Cesion de derechos
- VIV-NOT-001: Emision instruccion notarial
- VIV-AUT-001: Autoproduccion municipios
- VIV-TRA-001: Vivienda trabajadores
- VIV-ESC-001: Escriturar
- VIV-CIT-001: Citas IVEQ
```

### 12. APP - Soporte APPQRO
```
Keywords: appqro, app, aplicacion, ayuda app
Subcategories:
- APP-INF-001: Informacion y ayuda
- APP-AGE-001: Contactar agente
```

### 13. SOC - Programas Sociales SEDESOQ
```
Keywords: sedesoq, programa social, tarjeta contigo, beneficio social
Subcategories:
- SOC-TAR-001: Tarjeta contigo
```

## Agent Design Principles

### Knowledge Base Structure
Each agent maintains:
1. **Static Knowledge**: Links, contacts, locations, requirements
2. **Process Knowledge**: Step-by-step procedures
3. **FAQ Knowledge**: Common questions and answers
4. **Dynamic Tools**: APIs for real-time data (when available)

### Tool Categories
1. **Information Tools**: Return static/cached information
2. **Ticket Tools**: Create service requests
3. **Lookup Tools**: Query external systems (future)
4. **Handoff Tools**: Transfer to human agents

### Response Patterns
1. **Direct Answer**: When info is in knowledge base
2. **Guided Process**: Multi-step workflows
3. **Link Provision**: External portals/forms
4. **Escalation**: Complex cases to human agents

## Orchestrator Design

### Classification Pipeline
```
User Message
    |
    v
[Keyword Extraction] --> Fast match (O(1))
    |
    v (if no match)
[LLM Classification] --> Semantic understanding
    |
    v
[Entity Extraction] --> CURP, placa, folio, etc.
    |
    v
[Route to Agent] --> HTTP call with context
```

### Fallback Strategy
```
Primary Agent --> If fails --> ATC (Citizen Attention)
                            --> If unavailable --> Generic response
```

## Implementation Status

### Completed Agents (All 12 Specialized + 1 Fallback)

| Agent | Status | Knowledge Base | Key Features |
|-------|--------|----------------|--------------|
| TRA - Transport AMEQ | ✅ Complete | Tarjeta Preferente (4 types), QroBus, Tarifa UNIDOS | All requirements with URLs |
| VEH - Vehicles | ✅ Complete | Tenencia, Placas, Oficinas | Portal links included |
| EDU - Education USEBEQ | ✅ Complete | Preinscripciones, SAID, Vinculación Parental | Date-specific info |
| LAB - Labor CCLQ | ✅ Complete | Asesoría gratuita, Conciliación online | 2 locations + requirements |
| RPP - Registry | ✅ Complete | CERLIN, 8 certificate types, 6 locations | Costs in UMAs included |
| IQM - Women | ✅ Complete | Tel Mujer 24h, Emergency protocols | Crisis handling |
| PSI - Psychology SEJUVE | ✅ Complete | Ser Tranquilidad, Línea de la Vida | Crisis protocols |
| VIV - Housing IVEQ | ✅ Complete | 4 trámites, 3 programas, Citas system | WhatsApp links |
| CUL - Culture | ✅ Complete | 13 centros/museos, Cartelera | Google Maps links |
| APP - AppQRO | ✅ Complete | Soporte técnico, Portal ayuda | Troubleshooting guides |
| SOC - Social SEDESOQ | ✅ Complete | Tarjeta Contigo | WhatsApp support |
| ATC - Citizen Attention | ✅ Complete | All dependencies summary | Fallback/routing agent |

### Critical Contact Information

| Service | Emergency Line | Hours |
|---------|---------------|-------|
| Emergencias | 911 | 24/7 |
| Tel Mujer (IQM) | 442 216 47 57 | 24/7 |
| Línea de la Vida | 800-911-2000 | 24/7 |
| Atención Ciudadana | 4421015205 | Business hours |

### Agent File Structure

```
gobierno-queretaro/
├── orchestrator/
│   ├── classifier.py      # Hybrid keyword + LLM classification
│   └── router.py          # LangGraph routing logic
├── agents/
│   ├── transport-ameq/
│   │   ├── prompts.py     # Complete knowledge base
│   │   ├── agent.py       # LangGraph agent definition
│   │   └── tools.py       # Domain-specific tools
│   ├── vehicles/
│   │   └── ...
│   ├── education-usebeq/
│   │   └── ...
│   ├── labor-cclq/
│   │   └── ...
│   ├── registry-rpp/
│   │   └── ...
│   ├── women-iqm/
│   │   └── ...
│   ├── psychology-sejuve/
│   │   └── ...
│   ├── housing-iveq/
│   │   └── ...
│   ├── culture/
│   │   └── ...
│   ├── appqro/
│   │   └── ...
│   ├── social-sedesoq/
│   │   └── ...
│   └── citizen-attention/
│       └── ...            # Fallback agent
└── ARCHITECTURE.md
```

### prompts.py Pattern

Each agent's prompts.py contains:
```python
BASE_RULES = """..."""           # Shared conversation rules
KNOWLEDGE_BASE = """..."""       # Complete service information
{AGENT}_SYSTEM_PROMPT = """...""" # Full system prompt with rules + KB
PROMPTS = {                      # Task-specific prompts
    "task_type_1": "...",
    "task_type_2": "...",
    "inquiry": SYSTEM_PROMPT,    # Default fallback
}

def get_system_prompt(task_type: str = "inquiry") -> str
def get_base_rules() -> str
def get_knowledge_base() -> str
```

### Base Rules (Shared Across All Agents)

1. **RESPUESTAS CORTAS**: Máximo 2-3 oraciones, estilo WhatsApp
2. **UNA PREGUNTA POR MENSAJE**: No preguntas múltiples
3. **RESPUESTAS FORMATEADAS**: Usar "formatted_response" exactamente
4. **TRANSFERENCIA A HUMANO**: handoff_to_human cuando se solicite
5. **NO INVENTES INFORMACIÓN**: Solo usar knowledge base

### Special Crisis Protocols

**PSI (Psychology) and IQM (Women)** agents include special handling:
- Immediate provision of emergency numbers
- Empathetic tone requirements
- handoff_to_human for crisis situations
- Never leave user alone in crisis conversation

## CEA Agent (Water Services)

Note: CEA is handled by **maria-v3** separately and is not part of this multi-agent system. The orchestrator should route CEA-related queries to maria-v3.

## Next Steps

1. **Integrate with LangGraph**: Connect prompts.py to agent.py implementations
2. **Add Domain Tools**: Implement tools.py for each agent where APIs exist
3. **Test Classification**: Verify keyword mapping covers all user intents
4. **Deploy Orchestrator**: Set up routing between agents
5. **Add Monitoring**: Track which agents handle which queries
