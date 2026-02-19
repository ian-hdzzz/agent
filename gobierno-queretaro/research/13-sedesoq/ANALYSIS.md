# Programas Sociales SEDESOQ - Domain Research Analysis

## Executive Summary

**Priority 9 of 13** - High impact potential but complex implementation due to dignity preservation requirements and fraud prevention balance.

SEDESOQ (Secretaría de Desarrollo Social de Querétaro) manages social programs including Tarjeta Contigo, food programs, economic supports, and community development initiatives serving vulnerable populations.

| Factor | Score |
|--------|-------|
| User Volume | 5/10 |
| Current Pain | 9/10 |
| Impact Potential | 8/10 |
| Implementation Ease | 3/10 |
| **Overall** | **5.95/10** |

---

## 1. Current Menu Flow Analysis

### Existing Agent Limitations

The current social-sedesoq agent has significant gaps:

| Issue | Description |
|-------|-------------|
| Single program focus | Only Tarjeta Contigo addressed |
| External redirect | Immediately routes to WhatsApp (wa.me/5215618868513) |
| Missing programs | Food programs, economic supports not covered |
| No eligibility screening | Users can't check qualification |
| No status tracking | No way to check application progress |

### Programs NOT Currently Covered
- Comedores Comunitarios
- Despensas Alimentarias
- Apoyo a Adultos Mayores
- Apoyo a Personas con Discapacidad
- Vivienda Social (overlaps with IVEQ)
- Programas de Empleo Temporal
- Apoyo a Jefas de Familia

---

## 2. User Journey Mapping

### Journey A: New Benefit Application
```
Discovery → Information → Eligibility → Documents →
Submission → Verification → Approval → Delivery → Renewal
```

**Current**: Broken at Discovery (only 1 program visible)
**Enhanced**: Full conversational guidance through all steps

### Journey B: Status Check
**Current**: Requires office visits or phone calls
**Enhanced**: Real-time status via CURP lookup

### Journey C: Benefit Renewal
**Current**: No proactive notifications → benefit lapses
**Enhanced**: 90/60/30/7 day reminders before expiry

### Journey D: Problem Resolution
**Current**: WhatsApp only for Tarjeta Contigo
**Enhanced**: Intelligent issue routing for all programs

---

## 3. Pain Points Analysis

### Eligibility Complexity (HIGH)
- Multiple programs with overlapping criteria
- Users don't know what they qualify for
- Same documents requested repeatedly

### Documentation Burden (HIGH)
- Extensive requirements
- Users lack some documents
- No guidance on alternatives
- Repeated trips to offices

### Dignity Concerns (CRITICAL)
- Long visible queues feel stigmatizing
- Repeated disclosure of hardship
- Bureaucratic treatment
- Lack of privacy

### Access Barriers (HIGH)
- Low literacy populations
- Limited internet connectivity
- Elderly without smartphones
- Disabilities
- Indigenous language needs (Otomi)

### Status Opacity (HIGH)
- Cannot see application progress
- Unknown wait times
- No explanation for delays or denials

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P0** | Conversational Eligibility Screening | Natural conversation, not form-like interrogation |
| **P0** | Dignity-Preserving Language | Rights-based framing throughout |
| **P1** | Document Preparation Assistant | Interactive checklist with alternatives |
| **P1** | Real-Time Status Tracking | Via CURP lookup |
| **P1** | Proactive Renewal Notifications | 90/60/30/7 day reminders |
| **P2** | Tarjeta Contigo Self-Service | Balance, transactions, issue reporting |
| **P2** | Intelligent Issue Routing | Auto-categorization and assignment |
| **P3** | Multi-Language Support | Otomi for indigenous communities |

---

## 5. Required Integrations

### P0 - Critical
| System | Purpose |
|--------|---------|
| **Tarjeta Contigo API** | Balance, transactions, status, issues |
| **CURP Validation** | Via RENAPO federal registry |

### P1 - High
| System | Purpose |
|--------|---------|
| Beneficiary Management System | Profile, programs, applications |
| Eligibility Rules Engine | Pre-screening without personal data access |
| Notification Service | SMS, WhatsApp, push |

### P2 - Medium
| System | Purpose |
|--------|---------|
| Appointment System | Office visit scheduling |
| Mobile Brigade Schedules | Community visit calendar |

---

## 6. Dignity-Preserving Conversation Design

### Language Guidelines

**DO Use (Rights-Based):**
- "Tienes derecho a estos beneficios"
- "Estos programas están diseñados para apoyarte"
- "Vamos a revisar juntos las opciones disponibles"

**DON'T Use (Charity-Based):**
- ❌ "beneficencia", "caridad", "los pobres"
- ❌ "te vamos a ayudar porque lo necesitas"
- ❌ Language that implies judgment

### Income Discussion Approach
```
Bot: "Para verificar elegibilidad, ¿podrías indicarme
     en qué rango se encuentra el ingreso mensual
     de tu hogar?

     • Menos de $5,000
     • Entre $5,000 y $10,000
     • Entre $10,000 y $15,000
     • Más de $15,000

     Esta información es confidencial y solo se usa
     para identificar los programas disponibles para ti."
```

### Compassionate Denial Handling
```
Bot: "Revisé los criterios del programa [X] y en este
     momento no cumples con todos los requisitos.

     Sin embargo, encontré otros 2 programas para los
     que SÍ podrías calificar:

     1. [Programa alternativo A]
     2. [Programa alternativo B]

     ¿Te gustaría conocer más sobre alguno?"
```

### Confidentiality Assurance
Always include: "Tu información es confidencial y está protegida."

---

## 7. Knowledge Base Requirements

### Program Catalog (Expand from 1 to 10+)
- Tarjeta Contigo (current)
- Comedores Comunitarios
- Despensas Alimentarias
- Apoyo a Adultos Mayores
- Apoyo a Personas con Discapacidad
- Programas de Empleo Temporal
- Apoyo a Jefas de Familia
- Vivienda Social
- Becas Educativas
- Apoyo a Comunidades Rurales

### Per-Program Knowledge
- Eligibility criteria
- Document requirements (with alternatives)
- Application process
- Benefit amounts and frequency
- Renewal requirements
- Contact information

### Office and Service Locations
- SEDESOQ offices with hours
- Mobile brigade schedules by community
- Partner organizations (DIF, etc.)

---

## 8. Accessibility Considerations

### Low Literacy
- Simple language (3rd grade reading level)
- Voice input/output support
- Visual guides and icons
- Short messages

### Elderly Users
- Slower conversation pace
- Larger text (when applicable)
- Family assistance option
- Phone call fallback

### Disabilities
- Screen reader compatibility
- Voice navigation
- Text alternatives for all media

### Indigenous Communities
- Otomi language support (Phase 2)
- Cultural sensitivity in examples
- Community liaison integration

### Low Connectivity
- SMS fallback option
- Offline information packets
- Minimal data usage mode

---

## 9. Fraud Prevention with Dignity

### Balanced Approach

| Principle | Implementation |
|-----------|----------------|
| Backend fraud detection | Invisible to users |
| Non-accusatory verification | "Para confirmar tu identidad..." |
| Presumption of good faith | Default is trust |
| Proportional response | Risk-based, not blanket suspicion |
| Human review for flags | Not automated denial |
| Clear appeal mechanism | Always offer recourse |

### Verification Language
```
✅ Good: "Para proteger tu información, necesito
         verificar algunos datos..."

❌ Bad:  "Necesitamos comprobar que no hay fraude..."
```

---

## 8. Escalation Scenarios

### Immediate Escalation (URGENT)

| Trigger | Action |
|---------|--------|
| Food insecurity mentioned | Fast-track to food programs |
| Domestic violence indicators | IQM referral + safety protocol |
| Homelessness risk | Emergency housing resources |
| Medical emergency affecting benefits | Priority human handling |

### Standard Escalation

| Issue Type | Handling |
|------------|----------|
| Eligibility disputes | Human review with documentation |
| Benefit delays | Status investigation + timeline |
| Card issues | Tarjeta Contigo support line |
| Complex multi-program needs | Case manager assignment |

---

## Implementation Recommendations

### Phase 1 (Months 1-2)
- [ ] Expand program catalog to 5+ programs
- [ ] Implement dignified eligibility screening
- [ ] Add CURP-based status lookup
- [ ] Create document checklist tool

### Phase 2 (Months 3-4)
- [ ] Tarjeta Contigo API integration
- [ ] Proactive renewal notifications
- [ ] Mobile brigade schedule integration

### Phase 3 (Months 5-6)
- [ ] Full program catalog (10+)
- [ ] Multi-language support (Otomi)
- [ ] Accessibility enhancements

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Programs discoverable via AI | 10+ (vs 1 today) |
| Eligibility screening completion | >70% |
| Status check self-service | >80% |
| User dignity satisfaction | >4.5/5 |
| Fraud rate | No increase |
| Benefit enrollment rate | +20% |

---

## Key Files Referenced

- `agents/social-sedesoq/prompts.py` - Current agent prompts
- `agents/social-sedesoq/tools.py` - Current tools
- `research/synthesis/SENSITIVE_SERVICES_PROTOCOLS.md` - Vulnerable population protocols
- `research/synthesis/CONVERSATION_DESIGN_FRAMEWORK.md` - Design guidelines

---
*Research completed: 2026-02-04*
*⚠️ SENSITIVE SERVICE - Dignity preservation mandatory*
