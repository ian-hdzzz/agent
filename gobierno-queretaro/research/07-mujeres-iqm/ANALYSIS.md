# Atención a Mujeres (IQM) - Domain Research Analysis

## Executive Summary

**⚠️ TIER 1 SENSITIVE SERVICE - SAFETY CRITICAL**

The Instituto Queretano de la Mujer (IQM) domain serves women experiencing domestic violence, requiring legal assistance, psychological support, and economic empowerment.

**MANDATORY REQUIREMENTS:**
- Human oversight at all times
- 24/7 crisis escalation paths
- Enhanced privacy protections
- Safety-first conversation design
- Trauma-informed AI responses

| Factor | Score |
|--------|-------|
| User Volume | 3/10 |
| Current Pain | 7/10 |
| Impact Potential | 9/10 |
| Implementation Ease | 4/10 |
| **Overall** | **5.45/10** |

---

## 1. Current Menu Flow Analysis

### Existing Menu Structure

```
Atención a Mujeres (IQM)
├── 1. Contacto/Asesoría
│   └── Tel Mujer: 442 216 47 57 (24 horas)
│   └── Dirección: José María Pino Suárez #22, Col Centro
├── 2. Centros de Atención
│   └── "Contactar al Tel Mujer para conocer centros"
├── 3. Pasos ante Violencia
│   └── 1. Emergencias: 911
│   └── 2. Asesoría: Tel Mujer
│   └── 3. Atención presencial: Oficinas IQM
└── 4. Ubicación IQM
    └── Dirección + Google Maps link
```

### Critical Limitations

| Gap | Risk Level |
|-----|------------|
| **No danger assessment** | CRITICAL |
| **No safety planning** | HIGH |
| **No discrete interface** | HIGH |
| **No code word system** | HIGH |
| **Static information only** | MEDIUM |
| **No appointment scheduling** | MEDIUM |

---

## 2. User Journey Mapping

### Journey A: Active Violence - Immediate Danger

**Current**: Too slow, not discrete, no danger triage

**Required Flow**:
1. **Detection**: Keywords "violencia", "golpe", "peligro", "miedo"
2. **Immediate**: Display 911 prominently
3. **Assessment**: "¿Puedes contestar sí o no? ¿Estás en peligro AHORA?"
4. **Discrete Mode**: If yes, enter code-word mode
5. **Safety Plan**: Guide to safe contact method
6. **Handoff**: IMMEDIATE transfer to human crisis specialist

### Journey B: Seeking Legal Aid
- Divorce, custody, child support, protection orders
- Free legal aid available
- Appointment booking needed

### Journey C: Economic Empowerment
- Mujer Emprendedora (credits $10k-$50k)
- Capacitación Laboral
- Bolsa de Trabajo IQM

### Journey D: Psychological Support
- Individual therapy
- Group support sessions
- Crisis counseling

---

## 3. Pain Points Analysis

### Safety Concerns (CRITICAL)

| Pain Point | Severity |
|------------|----------|
| Abuser can see conversation | CRITICAL |
| No quick exit option | CRITICAL |
| Conversation history traceable | HIGH |
| WhatsApp notifications visible | HIGH |

### Privacy Concerns
- Sensitive conversations retained
- Name/CURP collection risks
- Fear of being "flagged" in systems

### Trust Barriers
- Institutional distrust
- AI skepticism in crisis
- Cultural stigma
- Fear of legal consequences

---

## 4. AI Enhancement Opportunities

### Discrete Interface Design
```yaml
discrete_mode:
  features:
    - quick_exit_button: "Salir rápido" → neutral site
    - fake_website_redirect: Display fake content option
    - no_persistent_notifications: Disable chat alerts
    - auto_delete_option: Clear conversation history
    - neutral_branding: Avoid "violence" words in UI
```

### Code Word System
```yaml
code_words:
  "pizza": Need help but cannot talk openly
  "medicina": Abuser is present, send disguised help
  "llueve": Send emergency contact immediately
  "farmacia": Need shelter information disguised
```

### Danger Assessment Protocol
```yaml
assessment_questions:
  - "¿Tienes miedo de tu pareja o alguien en tu casa?"
  - "¿Te han amenazado con hacerte daño a ti o a tus hijos?"
  - "¿Han usado armas o te han golpeado?"
  - "¿Has tenido que ir al hospital por golpes?"
  - "¿Controlan tu dinero, teléfono o con quién hablas?"

scoring:
  3+ yes: High risk → immediate safety planning
  1-2 yes: Medium risk → connect with advocate
  0 yes: Information seeking → provide resources
```

---

## 5. Required Integrations

### Emergency Services (CRITICAL)

| Service | Integration | Latency |
|---------|-------------|---------|
| 911 | Deep link/Click-to-call | IMMEDIATE |
| Tel Mujer Hotline | Warm transfer | < 30 seconds |
| Shelter Network | Secured API | < 5 seconds |

### IQM Internal Systems

| System | Priority |
|--------|----------|
| Case Management | HIGH |
| Appointment System | HIGH |
| Shelter Registry | CRITICAL |
| Legal Case Tracker | MEDIUM |

### Cross-Agency

- Fiscalía (Prosecutor) - Filing charges
- Juzgados Familiares - Protection orders
- DIF - Child protection
- Secretaría del Trabajo - Employment support

---

## 6. Conversation Design for Sensitive Topics

### Trauma-Informed Language

**DO use:**
- "Entiendo que esto es difícil."
- "No estás sola."
- "Buscar ayuda es un acto de valentía."
- "Tu bienestar es importante."
- "Lo que te pasó no es tu culpa."

**DO NOT use:**
- ❌ "¿Por qué no te vas?" (implies blame)
- ❌ "Deberías..." (judgmental)
- ❌ "¿Pero él te quiere?" (minimizing)
- ❌ "Piensa en tus hijos" (guilt-inducing)

### Violence Disclosure Response

```
[Keyword detected: "mi esposo me golpea"]

AI: Gracias por compartir esto conmigo. Lo que me cuentas es muy serio.
    Tu seguridad es lo más importante.

    ¿Estás en peligro en este momento?

[If YES]
AI: Por favor, llama al 911 ahora mismo.
    También puedes llamar a Tel Mujer: 442-216-4757 (24 horas).
    Te voy a conectar con una especialista de inmediato.
    [IMMEDIATE handoff + alert]

[If NO]
AI: Me alegra saber que estás a salvo por ahora.
    Quiero ayudarte a mantenerte segura.
    ¿Te gustaría hablar sobre opciones de apoyo?
```

---

## 7. SAFETY PROTOCOLS ⚠️

### Risk Level Definitions

| Level | Indicators | Response | Human |
|-------|-----------|----------|-------|
| **LEVEL 4** | Violence NOW, weapons | IMMEDIATE | MANDATORY |
| **LEVEL 3** | Recent escalation, threats | < 5 min | MANDATORY |
| **LEVEL 2** | Ongoing abuse, no immediate danger | < 24 hrs | Recommended |
| **LEVEL 1** | Information seeking | Standard | Optional |

### Level 4 - Imminent Danger Protocol

```
STEP 1 (0-10 seconds):
  AI: "Tu seguridad es lo más importante. Llama al 911 AHORA."
  [Display 911 prominently]
  [Trigger silent alert to IQM crisis team]

STEP 2 (10-30 seconds):
  AI: "¿Puedes salir de donde estás de forma segura?"

STEP 3 (30-60 seconds):
  AI: "Te estoy conectando con una especialista de inmediato."
  [IMMEDIATE handoff - NO QUEUE]

STEP 4 (Parallel):
  [System logs incident]
  [Alert to IQM supervisor]
  [Case created with URGENT flag]
```

### Human Handoff Requirements

| Level | Queue | Max Wait | Fallback |
|-------|-------|----------|----------|
| Level 4 | BYPASS | 0 sec | Tel Mujer immediate |
| Level 3 | Priority | 60 sec | Callback 15 min |
| Level 2 | Standard | 5 min | Callback 2 hrs |

---

## 8. Privacy and Confidentiality

### Data Classification

| Data Type | Classification | Retention |
|-----------|---------------|-----------|
| General inquiries | CONFIDENTIAL | 90 days |
| Violence disclosures | RESTRICTED | 10 years |
| Safety plans | RESTRICTED | 10 years |
| Shelter locations | RESTRICTED | Never stored |

### Mandatory Reporting (NOM-046-SSA2-2005)
- Child abuse must be reported to DIF
- Users must be informed: "En algunos casos, como cuando hay menores en riesgo, puede ser necesario reportar a las autoridades."

---

## 9. Mandatory Human Oversight

### Human-in-the-Loop Required For:
- All Level 3/4 risk assessments
- Any mandatory reporting situation
- First-time violence disclosure
- User requesting human
- AI uncertainty > 30%

### Crisis Team Structure
- **Crisis specialists**: 3-5 during business hours
- **On-call specialist**: 1 per shift (24/7)
- **Supervisor**: 1 per shift

### Training Requirements
- Domestic violence dynamics (16 hours)
- Trauma-informed care (8 hours)
- Safety planning (8 hours)
- Crisis intervention (16 hours)

---

## Emergency Contact Reference

| Service | Number | Hours |
|---------|--------|-------|
| **Emergencias** | **911** | **24/7** |
| **Tel Mujer** | **442-216-4757** | **24/7** |
| Línea de la Vida | 800-911-2000 | 24/7 |
| IQM Oficinas | 442-214-5700 | Business hours |
| DIF Querétaro | 442-212-6060 | Business hours |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Zero safety incidents | 100% |
| Crisis escalation time | < 30 seconds |
| Level 4 response time | < 60 seconds |
| Appropriate escalation | > 95% |
| AI containment rate | 60% (appropriate for this domain) |
| System availability | > 99.9% |

---

## Key Files Referenced

- `agents/women-iqm/prompts.py` - Current prompts
- `agents/women-iqm/tools.py` - Current tools
- `agents/women-iqm/agent.py` - LangGraph agent
- `research/synthesis/SENSITIVE_SERVICES_PROTOCOLS.md` - Safety protocols

---
*Research completed: 2026-02-04*
*⚠️ TIER 1 SENSITIVE SERVICE - Safety above efficiency*
