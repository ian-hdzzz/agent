# Conciliación Laboral CCLQ - Domain Research Analysis

## Executive Summary

**Priority 8 of 13** - High sensitivity due to emotional/financial stress of job loss situations.

The Centro de Conciliación Laboral de Querétaro (CCLQ) provides mandatory pre-litigation conciliation services for labor disputes as required by Mexico's 2019 labor reform.

**Critical Challenges:**
- 60-day statute of limitations creates urgency
- Mandatory in-person follow-up contradicts digital expectations
- Jurisdictional confusion post-November 3, 2021
- Emotionally vulnerable users experiencing financial stress

| Factor | Score |
|--------|-------|
| User Volume | 4/10 |
| Current Pain | 6/10 |
| Impact Potential | 8/10 |
| Implementation Ease | 5/10 |
| **Overall** | **5.60/10** |

---

## 1. Current Menu Flow Analysis

### Existing Menu Structure

```
Conciliación Laboral
├── 1. Asesoría Jurídica
│   ├── Info: Abogados gratuitos de Procuraduría
│   ├── Horario: 8:00 - 14:00
│   └── Ubicaciones: Querétaro, San Juan del Río
├── 2. Proceso de Conciliación
│   ├── Opción 1: Presencial en oficinas
│   ├── Opción 2: En línea (CENCOLAB)
│   └── ⚠️ ADVERTENCIA: Debe acudir a oficinas para iniciar
├── 3. Realizar Convenio
│   ├── Portal ratificación
│   └── Correo: ratificaciones@cclqueretaro.gob.mx
├── 4. Asunto Colectivo
│   └── Contacto: Lic. Miriam Rodríguez
├── 5. Información de Contacto
│   ├── Oficina Querétaro
│   └── Delegación San Juan del Río
└── 6. Asuntos Anteriores a Nov 2021
    └── Redirección a autoridad laboral previa
```

### Critical Limitations

| Issue | Impact |
|-------|--------|
| No urgency communication | Citizens may lose rights (60-day limit) |
| No rights assessment | Uninformed users underserved |
| No document guidance | Multiple office visits needed |
| No emotional support | Poor experience in crisis |
| Static hours info | Wasted trips |

---

## 2. User Journey Mapping

### Journey A: Wrongful Termination (Despido Injustificado)

| Phase | Emotion | Pain Points |
|-------|---------|-------------|
| Discovery (Day 0-3) | Shock/Fear | Doesn't know rights |
| Information (Day 4-10) | Anxiety | Legal jargon confusing |
| First Contact (Day 11-20) | Frustration | Online ≠ Complete |
| In-Person Visit (Day 21-30) | Overwhelmed | Missing documents |
| Conciliation (Day 31-45) | Stress | Employer no-shows |
| Resolution (Day 45-60) | Relief OR Fight | If no agreement → federal courts |

### Journey B: Unpaid Wages (Salarios Caídos)
- Small amounts feel not worthwhile
- Workers need money NOW, can't wait
- Some give up, employer wins by attrition

### Journey C: Voluntary Separation (Renuncia)
- Need calculator tool
- "What to ask for" guidance
- Meeting preparation help

---

## 3. Pain Points Analysis

### The 60-Day Statute of Limitations (CRITICAL)

**Article 518 LFT:**
> "Las acciones de trabajo prescriben en dos meses..."

| Issue | Impact |
|-------|--------|
| Awareness gap | Most workers don't know |
| Calculation confusion | Calendar vs business days |
| Practical impact | Days lost = rights lost forever |

### Mandatory In-Person Requirement

**The Digital Disconnect:**
- CENCOLAB allows online submission
- BUT process does NOT start until in-person visit
- Clock keeps running during false sense of security

### Jurisdictional Confusion (Post-Nov 2021)

| When | Where |
|------|-------|
| Before Nov 3, 2021 | Junta Local de Conciliación |
| After Nov 3, 2021 | CCLQ (state) or Federal Centers |

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P0** | Deadline Calculator | Calculate days remaining, urgency level |
| **P0** | Rights Assessment | Estimate finiquito/liquidación |
| **P1** | Document Checklist | Case-specific requirements |
| **P1** | Empathetic Responses | Crisis-aware conversation |
| **P2** | CENCOLAB Integration | Status check, appointments |
| **P2** | Employer Info Helper | RFC lookup guidance |

### Deadline Calculator Tool
```yaml
deadline_tool:
  input: termination_date
  output:
    days_remaining: int
    urgency_level: [green, yellow, orange, red, expired]
    recommended_action: string
```

### Rights Assessment (Compensation Formulas)
- **Indemnización 3 meses** = salario_diario_integrado × 90
- **20 días por año** = salario_diario_integrado × 20 × años
- **Aguinaldo** = salario_diario × 15 × (días/365)
- **Prima antigüedad** = 12 días por año (si 15+ años)

---

## 5. Required Integrations

### P0 - Critical
| System | Purpose |
|--------|---------|
| CENCOLAB | Case submission, status, appointments |
| Procuraduría | Legal advisory scheduling |

### P1 - High
| System | Purpose |
|--------|---------|
| Notification Service | Deadline reminders |
| Ticket System | Complex case tracking |

### P2 - Future
| System | Purpose |
|--------|---------|
| SAT/IMSS | Employer validation, salary verification |

---

## 6. Conversation Design for Emotional Situations

### Understanding Job Loss Emotions
Denial → Anger → Bargaining → Depression → Acceptance

### Design Principles
1. **Acknowledge First**, Information Second
2. **Normalize** the situation
3. **Provide Control** through clear options
4. **Avoid** bureaucratic language

### Crisis Detection Keywords

```yaml
financial_crisis:
  keywords: ["no tengo para comer", "desesperado"]
  action: expedited help, connect to SEDESOQ

workplace_abuse:
  keywords: ["me amenazaron", "acoso", "me golpearon"]
  action: safety check, handoff to human

mental_health:
  keywords: ["no sé qué hacer con mi vida", "muy deprimido"]
  action: Línea de la Vida (800-911-2000)
```

### Empathetic Response Template

```
"Lamento mucho lo que estás pasando. Perder el trabajo
de manera inesperada es muy difícil, y es normal
sentirse abrumado.

Quiero que sepas que tienes derechos y hay opciones para ti.

¿Me puedes compartir la fecha de tu último día de trabajo
para calcular los plazos importantes?"
```

---

## 7. Knowledge Base Requirements

### Ley Federal del Trabajo Key Articles

| Article | Topic | Plain Language |
|---------|-------|----------------|
| 518 | Prescripción | 60 días desde el despido |
| 48 | Despido injustificado | 3 meses de indemnización |
| 50 | 20 días por año | Por cada año trabajado |
| 162 | Prima antigüedad | 12 días/año si 15+ años |
| 684-A to E | Conciliación | Obligatorio antes de juicio |

### FAQ Bank (Required)
- ¿Qué es la conciliación laboral?
- ¿Cuánto tiempo tengo para reclamar?
- ¿Necesito abogado?
- ¿Qué pasa si mi patrón no se presenta?
- ¿Puedo reclamar si firmé mi renuncia?
- ¿Diferencia entre finiquito y liquidación?

---

## 8. Escalation Scenarios

### Immediate Human Handoff

| Trigger | Flag |
|---------|------|
| Complex legal question | LEGAL |
| Deadline < 7 days | URGENT |
| Workplace violence | SAFETY |
| Vulnerable population | VULNERABLE |

### Handoff Context Package
- Case type, termination date, days remaining
- Employer info collected
- Emotional state assessment
- Conversation summary
- Recommended actions

### Crisis Response

| Situation | Action |
|-----------|--------|
| Workplace violence | 911, IQM if gender-based |
| Financial crisis | Expedited options, SEDESOQ |
| Mental health | Línea de la Vida: 800-911-2000 |

---

## Contact Information

### CCLQ QUERÉTARO
- Dirección: Blvd. Bernardo Quintana 329, Centro Sur
- Teléfono: 442 195 41 61
- Horario: L-V 8:00 - 14:00

### CCLQ SAN JUAN DEL RÍO
- Dirección: Av. Panamericana 99 planta alta
- Teléfono: 427 101 25 47

### Portales
- CENCOLAB: https://queretaro.cencolab.mx/asesoria/seleccion
- Ratificación: https://www.cclqueretaro.gob.mx/index.php/tramites/ratificacion

---

## Success Metrics

| Metric | Current (Est.) | Target |
|--------|----------------|--------|
| Prescription expiration rate | 15-20% | <5% |
| First-visit document completeness | 40% | >80% |
| In-person visits per case | 2.5 avg | 1.5 avg |
| User satisfaction | Unknown | >4.2/5 |
| Resolution time | ~30 days | ~20 days |

---

## Key Files Referenced

- `agents/labor-cclq/prompts.py` - Knowledge base
- `agents/labor-cclq/tools.py` - Deadline calculator stubs
- `agents/labor-cclq/agent.py` - LangGraph agent

---
*Research completed: 2026-02-04*
*⚠️ HIGH SENSITIVITY - Financial/emotional stress*
