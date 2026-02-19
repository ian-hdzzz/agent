# Educación Básica USEBEQ - Domain Research Analysis

## Executive Summary

**Priority 4 of 13** - Time-critical domain with highest stress period during enrollment (February 3-13).

USEBEQ (Unidad de Servicios para la Educación Básica del Estado de Querétaro) handles basic education services including preschool, primary, and secondary school enrollment, scholarships, certificates, and parent support.

| Factor | Score |
|--------|-------|
| User Volume | 7/10 (seasonal spikes) |
| Current Pain | 8/10 |
| Impact Potential | 9/10 |
| Implementation Ease | 6/10 |
| **Overall** | **7.55/10** |

---

## 1. Current Menu Flow Analysis

### Existing Flow Structure

```
EDUCACION BASICA (USEBEQ)
|
+-- 1. Verifica Vinculación
|   +-- Input: CURP del aspirante
|       +-- If found: Show vinculación status + reprint option
|       +-- If not found: Error messages about CURP or timing
|
+-- 2. Preinscripciones
|   +-- Input: CURP del aspirante
|       +-- If preasignación exists: Show assignment
|       +-- If not: Redirect to www.usebeq.edu.mx/said
|
+-- 3. Asesoría Educativa
    +-- Transfer to human agent
```

### Flow Limitations

| Issue | Description | Impact |
|-------|-------------|--------|
| Linear-only navigation | Users must know exact option number | High dropout |
| No natural language | Can't ask "¿Cómo inscribo a mi hijo?" | Frustration |
| Context loss | Each interaction starts fresh | Repeat data entry |
| No guidance | Assumes parent knows terminology | Confusion |
| Time-insensitive | No dynamic messaging based on current period | Missed deadlines |
| Error handling | Generic "CURP not found" with no help | Abandonment |

---

## 2. User Journey Mapping

### Primary User Personas

**Persona 1: Anxious First-Time Parent**
- Enrolling first child in preescolar (age 3-6)
- Knowledge Level: Low
- Emotional State: Anxious, worried about school quality
- Questions: "¿Mi hijo tiene 4 años, puede entrar a kinder?"

**Persona 2: Experienced Parent (Transition)**
- Child transitioning between levels (kinder→primaria, primaria→secundaria)
- Knowledge Level: Medium
- Emotional State: Moderately stressed

**Persona 3: Problem-Solver Parent**
- Dealing with special circumstances (address change, late registration, special needs)
- Emotional State: Highly stressed

### Critical Journey: Enrollment Period (February 3-13)

| Phase | Dates | Current State | Pain Level |
|-------|-------|---------------|------------|
| Vinculación Parental | Early Jan - Jan 16 | Menu gives dates only | Medium |
| Anxiety Period | Jan 17 - Feb 2 | Static "deadline passed" | High |
| **High-Volume Phase** | **Feb 3-13** | CURP lookup + redirect | **Critical** |
| Post-Enrollment | After Feb 13 | No proactive updates | High |

---

## 3. Pain Points Analysis

### Critical Pain Points

| Pain Point | Severity | Description |
|------------|----------|-------------|
| Terminology Confusion | HIGH | "Vinculación Parental", "SAID", "Preasignación" - parents don't understand |
| Document Requirements | HIGH | Unclear which need originals vs copies |
| No Status Visibility | HIGH | Can't confirm registration receipt |
| System Overload | CRITICAL | SAID website crashes Feb 3-13 |
| School Selection | MEDIUM-HIGH | No info about nearby schools |
| Special Circumstances | HIGH | No guidance for disabilities, late arrivals |
| Time-Critical Stress | CRITICAL | 10-day window creates panic |

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P0** | Intelligent Enrollment Guide | Conversational wizard with age verification, document checklist |
| **P0** | Stress-Aware Support | Detect anxiety, use calming language, always offer alternatives |
| **P1** | Dynamic Status Dashboard | Real-time SAID integration, push notifications |
| **P1** | School Finder | Geolocation-based recommendations with capacity info |
| **P2** | Document Preparation Assistant | Interactive checklist, acquisition guidance |
| **P2** | Proactive Reminders | Deadline alerts based on child's age |
| **P3** | Special Circumstances Navigator | Flows for transfers, late enrollment, USAER |

---

## 5. Required Integrations

### P0 - Critical
| System | Endpoints Needed |
|--------|------------------|
| **SAID System** | `check_vinculacion`, `check_preasignacion`, `get_enrollment_status`, `submit_enrollment` |

### P1 - High
| System | Purpose |
|--------|---------|
| School Directory | Search by location, get school details by CCT |
| CURP Validation | Validate format, extract age, check cutoff eligibility |
| Notification Service | Enrollment reminders, status changes, assignment alerts |
| Case Management | Education-specific tickets |

### P2 - Medium
| System | Purpose |
|--------|---------|
| Scholarship Systems | Available programs, application status |

---

## 6. Conversation Design for Parents

### Tone Guidelines
- **Warm, supportive, reassuring**
- Use parent language: "tu hijo/hija" not "el aspirante"
- Avoid bureaucratic terms
- Acknowledge stress: Enrollment is emotional
- Provide certainty: Even "wait" needs clear next steps
- Celebrate progress: "¡Excelente, ya tienes la mitad de los documentos!"

### Handling Stress and Anxiety

**Stress Indicators:**
- ALL CAPS messages
- Multiple exclamation points
- Words like "urgente", "desesperado"
- Repeated attempts at same question

**Response Strategy:**
```
1. ACKNOWLEDGE: "Entiendo que esto es estresante..."
2. PROVIDE CERTAINTY: "La buena noticia es que todavía hay tiempo..."
3. GIVE CONTROL: "Aquí están tus opciones..."
4. OFFER HUMAN: "Si prefieres, puedo conectarte con un asesor..."
```

### Sample Conversation

```
Parent: "MI HIJO TIENE 5 AÑOS Y NO SE SI PUEDO INSCRIBIRLO YA ME DESESPERE!!!"

Bot: "Entiendo tu preocupación, y estoy aquí para ayudarte. 🤗

     Con 5 años, tu hijo puede entrar a 3° de preescolar o
     1° de primaria, dependiendo de su fecha de nacimiento.

     ¿Me compartes su CURP para verificar exactamente
     qué nivel le corresponde?"
```

---

## 7. Knowledge Base Requirements

### Static Knowledge
- **Enrollment Calendar 2026-2027** (all key dates)
- **Requirements by Level** (preescolar, primaria, secundaria)
- **Scholarship Programs** (excelencia, apoyo, transporte)
- **Contact Information** (USEBEQ offices, hotlines)
- **FAQ Bank** (30+ common questions)

### Dynamic Knowledge (API Integration)
- Current enrollment counts by school
- Real-time SAID system status
- Individual enrollment status
- School capacity availability

---

## 8. Escalation Scenarios

### Immediate Escalation (URGENT)

| Trigger | Action |
|---------|--------|
| Parent reports abuse/neglect at school | Immediate handoff + capture details |
| Parent mentions suicidal thoughts (student) | Crisis protocol + emergency resources |
| System failure on last day of enrollment | Priority callback queue |

### Standard Escalation

| Issue Type | Ticket Code | SLA |
|------------|-------------|-----|
| Complex Enrollment Issues | EDU-ENR-002 | 24-48hr |
| School Assignment Appeals | EDU-ASN-001 | Appointment |
| School Complaints | EDU-QUE-001 | 800-841-0022 |

### Human Handoff Protocol
Required: conversation summary, parent name, child CURP, issue type, emotional state, preferred callback time

---

## Implementation Recommendations

### Phase 1: Pre-Enrollment (January)
- [ ] Finalize 2026-2027 calendar dates
- [ ] Update all document requirements
- [ ] Build FAQ responses
- [ ] Create school directory integration
- [ ] Implement enrollment guidance wizard
- [ ] Build stress-aware response patterns

### Phase 2: Enrollment Period (February 3-13)
- [ ] Real-time conversation volume tracking
- [ ] System status dashboard
- [ ] Escalation queue management
- [ ] Predefined messages for system outages
- [ ] Extended callback hours

### Phase 3: Post-Enrollment (March+)
- [ ] Assignment publication notifications
- [ ] Appeal process guidance
- [ ] Scholarship application support

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Enrollment inquiries resolved without human | 60% |
| Parent satisfaction during enrollment | 4.0/5 |
| Average conversation length | <8 turns |
| Escalation rate | <20% |
| System availability during peak | 99.5% |
| Time to human response (escalations) | <30 min |

---

## Key Files Referenced

- `agents/education-usebeq/agent.py` - Task classification
- `agents/education-usebeq/tools.py` - Enrollment, scholarship, school search tools
- `agents/education-usebeq/prompts.py` - Knowledge base with SAID references
- `ARCHITECTURE.md` - EDU category code

---
*Research completed: 2026-02-04*
*⚠️ TIME-CRITICAL: Enrollment period February 3-13*
