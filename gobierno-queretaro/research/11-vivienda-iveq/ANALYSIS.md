# Instituto de Vivienda IVEQ - Domain Research Analysis

## Executive Summary

**Priority 7 of 13** - Housing is a fundamental human need requiring dignity-preserving interactions.

The Instituto de Vivienda del Estado de Querétaro (IVEQ) provides housing programs, property regularization, and administrative services for citizens seeking affordable housing solutions.

| Factor | Score |
|--------|-------|
| User Volume | 4/10 |
| Current Pain | 6/10 |
| Impact Potential | 7/10 |
| Implementation Ease | 6/10 |
| **Overall** | **5.60/10** |

---

## 1. Current Menu Flow Analysis

### Service Structure

IVEQ organizes services into three main categories:

```
Instituto de Vivienda (IVEQ)
├── Trámites y Servicios (4 procedures)
│   ├── Constancia de No Adeudo
│   ├── Expedición de Copias/Planos
│   ├── Cesión de Derechos
│   └── Emisión de Instrucción Notarial
├── Programas de Vivienda (3 programs)
│   ├── Autoproducción en Municipios
│   ├── Vivienda para Trabajadores del Estado
│   └── Escrituración/Regularización
└── Sistema de Citas
    └── citas.iveq.gob.mx
```

### Communication Channels

| Channel | Purpose |
|---------|---------|
| WhatsApp (Trámites) | Administrative procedures |
| WhatsApp (Programas) | Housing programs |
| Phone: 442 192 9200 | Main line with extensions |
| Web Portal | Information and appointments |

---

## 2. User Journey Mapping

### Journey A: First-Time Home Seeker

| Phase | User State | Pain Points |
|-------|-----------|-------------|
| 1. Discovery | Hopeful, uncertain | Scattered information |
| 2. Eligibility Check | Anxious | Unclear requirements |
| 3. Document Gathering | Overwhelmed | Long lists, unclear alternatives |
| 4. Application | Stressed | Complex forms |
| 5. Waiting | Anxious | No status visibility |
| 6. Resolution | Relieved or Disappointed | No follow-up support |

### Journey B: Property Regularization

**Persona**: Don José, owns home 20 years without title

| Phase | Challenge |
|-------|-----------|
| 1. Awareness | Doesn't know regularization exists |
| 2. Requirements | Proving long-term possession |
| 3. Documentation | Missing old records |
| 4. Processing | Unknown timeline |
| 5. Resolution | Finally gets escritura |

### Journey C: Transfer of Rights (Cesión de Derechos)

- Family property transfers
- Inheritance situations
- Requires both parties' presence

---

## 3. Pain Points Analysis

### Bureaucratic Complexity (HIGH)
- Requirements scattered across multiple pages
- Unclear eligibility criteria
- Legal jargon without explanation
- Multiple office visits required

### Process Opacity (HIGH)
- No status tracking available
- Unknown timelines ("depends on case")
- No proactive updates
- Must call repeatedly for status

### Accessibility Barriers (MEDIUM)
- Limited office hours (8am - 3pm)
- Busy phone lines
- Non-mobile-friendly website
- Physical presence required for most steps

### Emotional Burden (HIGH)
- Anxiety about home ownership
- Fear of rejection
- Financial stress
- Long wait times create uncertainty

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P0** | Eligibility Screening | Conversational pre-qualification |
| **P0** | Document Guidance | Interactive checklists with alternatives |
| **P1** | Status Tracking | Folio-based lookup with stage visibility |
| **P1** | Appointment Scheduling | Natural language booking |
| **P2** | Financial Calculator | Cost estimation, payment planning |
| **P2** | Alternative Pathways | INFONAVIT, FOVISSSTE guidance |

### Intelligent Eligibility Screening

```
Bot: "Para ayudarte a encontrar el programa adecuado,
     necesito hacerte algunas preguntas.

     ¿Cuál es tu situación laboral actual?

     • Empleado del gobierno del estado
     • Empleado del sector privado
     • Trabajador independiente
     • Otro"

[Branches based on response to determine program fit]
```

### Document Guidance System

```
Bot: "Para el programa de Escrituración necesitas:

     ✅ Identificación oficial (INE o pasaporte)
     ✅ CURP
     ✅ Comprobante de domicilio (no mayor a 3 meses)
     ✅ Acta de nacimiento
     ⚠️ Comprobante de posesión del inmueble

     ¿Tienes alguna duda sobre algún documento?"
```

---

## 5. Required Integrations

### HIGH Priority

| System | Purpose |
|--------|---------|
| Case Management | Application tracking |
| Appointment System | citas.iveq.gob.mx integration |

### MEDIUM Priority

| System | Purpose |
|--------|---------|
| Property Database | Verify property eligibility |
| RPP Cross-Agent | Registry coordination |

### Shared Services

| Service | Purpose |
|---------|---------|
| CURP Validation | Identity verification |
| Notifications | Status updates |
| Payment Gateway | Fee processing |
| Document Manager | Upload handling |

---

## 6. Conversation Design for Dignity

### Core Principles

Housing is a fundamental human need. Every interaction must:

1. **Acknowledge significance** of home ownership dreams
2. **Use income ranges** instead of exact numbers
3. **Normalize questions** about financial situation
4. **Provide alternatives** even in rejection
5. **Recognize family situations** (single parents, multigenerational, disabilities)

### Income Discussion Approach

```
Bot: "Para determinar qué programas aplican para ti,
     ¿podrías indicarme el rango de ingreso mensual
     de tu hogar?

     • Menos de $10,000
     • Entre $10,000 y $20,000
     • Entre $20,000 y $35,000
     • Más de $35,000

     Esta información es confidencial y solo se usa
     para identificar los programas disponibles."
```

### Handling Rejection with Dignity

```
Bot: "Con base en la información que me compartiste,
     el programa de Vivienda para Trabajadores del Estado
     no aplica en tu caso porque está diseñado para
     empleados del gobierno estatal.

     Sin embargo, tengo otras opciones para ti:

     1. INFONAVIT - Si tienes empleo formal
     2. FOVISSSTE - Si eres empleado federal
     3. Programa de Autoproducción - Para construir
        en terreno propio

     ¿Te gustaría conocer más sobre alguna opción?"
```

---

## 7. Knowledge Base Requirements

### Programs (3)

| Program | Target | Key Requirements |
|---------|--------|------------------|
| Autoproducción | Families with land | Proof of land ownership |
| Vivienda Trabajadores | State employees | Employment proof |
| Escrituración | Long-term occupants | Possession proof |

### Trámites (4)

| Trámite | Purpose | Requirements |
|---------|---------|--------------|
| Constancia No Adeudo | Prove no debt | IVEQ property |
| Copias/Planos | Get property plans | Folio number |
| Cesión Derechos | Transfer property | Both parties present |
| Instrucción Notarial | Start notarization | Previous steps complete |

### FAQs

- ¿Qué programas de vivienda hay?
- ¿Cuáles son los requisitos para...?
- ¿Cuánto tiempo tarda el trámite?
- ¿Cómo reviso el estado de mi solicitud?
- ¿Qué hago si me rechazan?

---

## 8. Escalation Scenarios

### Escalation Matrix

| Trigger | Response Time | Action |
|---------|---------------|--------|
| User requests human | Immediate | Transfer |
| Complex eligibility | 5 min | Human review |
| Legal complications | 30 min | Legal team callback |
| Complaints | 1 hour | Supervisor review |

### After-Hours Protocol

- Information-only mode
- No appointment booking
- Collect contact for callback
- Emergency housing resources (if crisis)

---

## Contact Information

### IVEQ Main Office
- Dirección: [Office address]
- Teléfono: 442 192 9200
- Horario: L-V 8:00 - 15:00

### Online Services
- Citas: citas.iveq.gob.mx
- Portal: www.iveq.gob.mx

### WhatsApp Lines
- Trámites: [Number]
- Programas: [Number]

---

## Success Metrics

| Metric | Current (Est.) | Target |
|--------|----------------|--------|
| Eligibility screening completion | Unknown | >75% |
| Document list helpfulness | Unknown | >4.0/5 |
| Application status self-service | 0% | >60% |
| User dignity satisfaction | Unknown | >4.5/5 |

---

## Implementation Timeline

### Phase 4 (Months 10-12)

- [ ] Eligibility screening flow
- [ ] Document guidance system
- [ ] Appointment integration
- [ ] Status tracking (if API available)
- [ ] Alternative pathways guidance

---

## Key Files Referenced

- `agents/housing-iveq/agent.py` - Current implementation
- `agents/housing-iveq/tools.py` - Program info, eligibility
- `agents/housing-iveq/prompts.py` - Knowledge base

---
*Research completed: 2026-02-04*
*Priority: 7/13 (Dignity-preserving housing services)*
