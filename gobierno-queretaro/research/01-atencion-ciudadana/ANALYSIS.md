# Atención Ciudadana (Citizen Services) - Domain Research Analysis

## Executive Summary

**Priority 6 of 13** - Catch-all service that handles wide variety of intents and routes to other domains.

Atención Ciudadana serves as the primary entry point and fallback for citizen inquiries that don't match other specialized domains. It handles general inquiries, complaints, suggestions, directory lookups, and emergency information.

| Factor | Score |
|--------|-------|
| User Volume | 6/10 |
| Current Pain | 9/10 |
| Impact Potential | 7/10 |
| Implementation Ease | 4/10 |
| **Overall** | **6.30/10** |

---

## 1. Current Menu Flow Analysis

### Existing Menu Structure

```
Atención Ciudadana
├── 1. Contacto
│   └── Tel: 4421015205
├── 2. Servicios (12 departamentos)
│   ├── Transporte
│   ├── Agua
│   ├── Educación
│   ├── ... (routes to specialists)
├── 3. Quejas y Sugerencias
│   └── Form submission
└── 4. Emergencias
    └── 911, Tel Mujer, etc.
```

### Current Implementation

The orchestrator uses a hybrid classification approach:
- **Keyword matching** for high-confidence routes
- **LLM classification** for ambiguous queries
- **Fallback to ATC** when confidence < threshold

### Critical Limitations

| Gap | Description |
|-----|-------------|
| Menu fatigue | Citizens abandon after 3+ levels |
| Keyword mismatches | Common phrasing not recognized |
| No context retention | Each interaction starts fresh |
| Dead-end responses | No next steps provided |
| Generic fallback | "Contacta a un agente" for everything |

---

## 2. User Journey Mapping

### Journey A: General Inquiry
```
Citizen: "¿Cuáles son los horarios de atención?"

Current: Generic response or redirect to website
Enhanced: Context-aware response based on detected topic
```

### Journey B: Complaint Submission
```
Citizen: "Quiero poner una queja sobre un funcionario"

Current: "Envía tu queja a [email]"
Enhanced: Structured intake → Category → Details → Ticket → Tracking
```

### Journey C: Department Routing
```
Citizen: "Necesito hablar con alguien de tránsito"

Current: Keyword match → Route to Transporte
Enhanced: Clarify intent → Route with context → Warm handoff
```

### Journey D: Emergency Information
```
Citizen: "¿Cuál es el número de emergencias?"

Current: Static list of numbers
Enhanced: Assess urgency → Appropriate resource → Follow-up
```

---

## 3. Pain Points Analysis

### Menu Navigation Fatigue (HIGH)
- Citizens don't know which category applies
- 3+ level deep menus cause abandonment
- Estimated 35% abandonment rate

### Keyword Mismatches (HIGH)
- "quiero saber de mi multa" → doesn't match "Vehículos"
- "el agua está sucia" → might not route to CEA
- Synonyms and colloquial terms not recognized

### No Context Retention (MEDIUM)
- Citizen explains issue → routed → must re-explain
- Previous interactions not considered
- No cross-session memory

### Dead-End Responses (HIGH)
- "No entendí tu mensaje" with no guidance
- No alternative suggestions
- No proactive clarification

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Impact | Effort |
|----------|-------------|--------|--------|
| **P0** | Natural Language Understanding | High | Medium |
| **P0** | Intelligent Routing | High | Medium |
| **P1** | Structured Complaint Workflow | High | Medium |
| **P1** | Empathy Detection | Medium | Low |
| **P2** | Proactive Service Suggestions | Medium | High |
| **P2** | Cross-Session Context | Medium | High |

### Natural Language Understanding
Replace keyword matching with semantic understanding:
```
"quiero saber cuánto debo" → Detect: debt inquiry
"mi calle está oscura" → Detect: street lighting report
"necesito un papel" → Clarify: what document?
```

### Intelligent Routing
Confidence-based routing with fallback:
```python
if confidence > 0.85:
    route_to_specialist(domain)
elif confidence > 0.60:
    clarify_intent()
else:
    handle_in_atc()  # Don't route uncertain queries
```

### Structured Complaint Workflow
```
1. Detect complaint intent
2. Categorize: service, employee, infrastructure, other
3. Collect: location, date, description, evidence
4. Create ticket with SLA
5. Provide tracking number
6. Schedule follow-up
```

---

## 5. Required Integrations

### P0 - Critical
| System | Purpose |
|--------|---------|
| Government Directory | Dynamic phone/hours lookup |
| Ticket/CRM System | Complaint creation and tracking |
| Chatwoot | Human handoff with context |

### P1 - High
| System | Purpose |
|--------|---------|
| Cross-Agent Context | Transfer context between specialists |
| Notification Service | Status updates to citizens |

### P2 - Medium
| System | Purpose |
|--------|---------|
| Analytics Dashboard | Track routing accuracy, resolution rates |
| Satisfaction Surveys | Post-interaction feedback |

---

## 6. Conversation Design Recommendations

### Progressive Disclosure
Don't overwhelm with options. Ask clarifying questions:
```
Citizen: "Tengo un problema"

Bot: "Entiendo. Para ayudarte mejor, ¿tu problema está relacionado con:
     • Un servicio del gobierno (agua, transporte, trámites)
     • Una queja o sugerencia
     • Información general
     • Algo urgente"
```

### Empathy-First Responses
For frustrated citizens:
```
Citizen: "NADIE ME AYUDA Y YA LLEVO 3 DÍAS CON ESTE PROBLEMA!!!"

Bot: "Entiendo tu frustración, y lamento que hayas tenido esta experiencia.
     Quiero asegurarme de que tu caso se resuelva.

     ¿Me puedes contar qué ha pasado para poder escalarlo correctamente?"
```

### Seamless Handoff
When routing to specialist:
```
Bot: "Por lo que describes, el equipo de Agua (CEA) puede ayudarte mejor.

     Te voy a transferir. Ellos ya tendrán el contexto de lo que me
     compartiste, así que no necesitas repetir todo.

     ¿Hay algo más que quieras que les comparta?"
```

---

## 7. Knowledge Base Requirements

### Static Knowledge
- **Government Directory**: All departments with phones, hours, addresses
- **Emergency Contacts**: 911, Tel Mujer, Línea de la Vida, etc.
- **FAQs**: Top 50 general questions with answers
- **Service Catalog**: What each department handles

### Dynamic Knowledge (API)
- Office hours (holidays, special schedules)
- Service alerts (system outages, closures)
- Wait times for phone lines

### Complaint Categories
| Category | SLA | Escalation |
|----------|-----|------------|
| Service quality | 5 business days | Supervisor |
| Employee conduct | 3 business days | HR + Supervisor |
| Infrastructure | 10 business days | Public Works |
| Urgent safety | 24 hours | Immediate |

---

## 8. Escalation Scenarios

### 5 Escalation Levels

| Level | Trigger | Action |
|-------|---------|--------|
| 1 | Bot uncertainty | Clarify within bot |
| 2 | Citizen frustration | Offer human agent |
| 3 | Complex multi-domain | Transfer with context |
| 4 | Complaint/formal | Create ticket + human |
| 5 | Emergency | Immediate + emergency numbers |

### Handoff Protocol

Context package includes:
- Conversation summary
- Detected intent and confidence
- Citizen sentiment (frustrated, neutral, etc.)
- Collected entities (names, dates, locations)
- Attempted solutions

### Post-Escalation Flow
```
After human handles:
1. Log resolution
2. Send satisfaction survey
3. If unresolved: schedule follow-up
4. Update knowledge base if new pattern
```

---

## Success Metrics

| Metric | Current (Est.) | Target |
|--------|----------------|--------|
| Resolution rate | 40% | 70%+ |
| Correct routing | 60% | 90%+ |
| Abandonment rate | 35% | <15% |
| CSAT | Unknown | 4.0+/5.0 |
| Avg. turns to resolution | 8+ | <5 |

---

## Implementation Phases

### Phase 1 (Weeks 1-2)
- [ ] Deploy agent with orchestrator integration
- [ ] Basic ticket creation for complaints
- [ ] Emergency information flow

### Phase 2 (Weeks 3-4)
- [ ] Dynamic directory integration
- [ ] FAQ knowledge base
- [ ] Cross-agent context transfer

### Phase 3 (Weeks 5-6)
- [ ] Empathy detection
- [ ] Satisfaction surveys
- [ ] Analytics dashboard

---

## Risk Analysis

| Risk | Mitigation |
|------|------------|
| Misrouting frustrates citizens | Confidence thresholds + clarification |
| Complaint backlog | Clear SLAs + escalation paths |
| Context loss on handoff | Structured context package |
| Over-reliance on fallback | Continuous routing accuracy monitoring |

---

## Key Files Referenced

- `agents/citizen-attention/agent.py` - LangGraph agent with task handlers
- `agents/citizen-attention/tools.py` - Directory, tickets, handoff
- `agents/citizen-attention/prompts.py` - Knowledge base
- `orchestrator/classifier.py` - 13-category intent classification
- `orchestrator/router.py` - LangGraph router with circuit breaker

---
*Research completed: 2026-02-04*
*Priority: 6/13 (Catch-all + Router)*
