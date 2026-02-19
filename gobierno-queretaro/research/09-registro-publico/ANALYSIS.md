# Registro Público de la Propiedad (RPP) - Domain Research Analysis

## Executive Summary

**Priority 5 of 13** - Complex domain serving both citizens and professionals (notaries, lawyers).

The Registro Público de la Propiedad handles property registry services including certificates, property searches, mortgage cancellations, and registry alerts across 6 regional subdirections.

| Factor | Score |
|--------|-------|
| User Volume | 5/10 |
| Current Pain | 7/10 |
| Impact Potential | 8/10 |
| Implementation Ease | 5/10 |
| **Overall** | **6.30/10** |

---

## 1. Current Menu Flow Analysis

### Service Structure

The RPP service has 22 distinct subcategories:

```
Registro Público (RPP)
├── ConsultasSire (Property Search)
│   ├── By Catastral Number
│   ├── By Folio Real
│   └── By Address
├── CERLIN Account Management
│   ├── Registration
│   ├── Password Recovery
│   └── Account Issues
├── Certificates (8 types)
│   ├── Libertad de Gravamen
│   ├── Existencia/Inexistencia
│   ├── Inscripción
│   ├── Antecedentes
│   ├── No Propiedad
│   ├── Certificación de Documentos
│   ├── Constancia de Vigencia
│   └── Certificación de Firmas
├── Property Procedures
│   ├── Mortgage Cancellation
│   ├── Inheritance
│   └── Judicial Matters
├── Alerta Registral (Fraud Alerts)
└── Status Tracking
```

### 6 Regional Subdirections
- Querétaro Centro
- Querétaro Sur
- San Juan del Río
- Tequisquiapan
- Cadereyta
- Jalpan

---

## 2. User Journey Mapping

### Journey A: Certificate Request (Citizen)

**Current Pain Points:**
```
1. User doesn't know which of 8 certificates they need
2. Needs folio real but doesn't know how to find it
3. Must register for CERLIN account (2-day delay)
4. Multiple systems: ConsultasSire → CERLIN → Portal
5. No status notifications
```

**Enhanced Flow:**
```
User: "Necesito un certificado de mi casa"

Bot: "Para ayudarte a elegir el certificado correcto,
     ¿para qué lo necesitas?

     • Vender mi propiedad
     • Trámite bancario/hipoteca
     • Verificar que no hay adeudos
     • Trámite legal/herencia
     • Otro"

[Routes to appropriate certificate type]
```

### Journey B: Property Search (Professional)

**Notary/Lawyer Needs:**
- Batch processing (multiple folios)
- Quick lookups without explanation
- API integration for their systems
- Priority queue
- Tracking across multiple requests

---

## 3. Pain Points Analysis

### Citizen Pain Points

| Issue | Severity |
|-------|----------|
| 8 certificate types cause confusion | HIGH |
| Terminology unclear (gravamen, folio real) | HIGH |
| Multi-system fragmentation | MEDIUM |
| 2-day CERLIN registration delay | MEDIUM |
| No proactive notifications | MEDIUM |

### Professional Pain Points

| Issue | Severity |
|-------|----------|
| No batch processing | HIGH |
| No API integration | HIGH |
| No priority queue | MEDIUM |
| Manual tracking | MEDIUM |

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P0** | Certificate Selector | Guide to right certificate based on need |
| **P0** | Folio Lookup Helper | Find folio from catastral or address |
| **P1** | CERLIN Registration Guide | Step-by-step with rejection prevention |
| **P1** | Status Tracking | Proactive notifications |
| **P2** | Professional Portal | Batch features, API access |
| **P2** | Rejection Resolution | Help fix common issues |
| **P3** | Alerta Registral | Simplified enrollment |

### Certificate Selector Logic

```yaml
certificate_decision_tree:
  selling_property:
    - Libertad de Gravamen (prove no liens)
    - Antecedentes (full history if buyer requests)

  bank_loan:
    - Libertad de Gravamen
    - Certificación de Documentos (if bank needs certified copies)

  inheritance:
    - Existencia/Inexistencia (verify property exists in registry)
    - Antecedentes (trace ownership chain)

  verify_no_debts:
    - Libertad de Gravamen

  legal_proceeding:
    - Certificación de Documentos
    - Constancia de Vigencia
```

---

## 5. Required Integrations

### P0 - Critical

| System | Purpose |
|--------|---------|
| **CERLIN** | Certificate requests, status, accounts |
| **ConsultasSire** | Property search by catastral/folio/address |

### P1 - High

| System | Purpose |
|--------|---------|
| Payment Gateway | SPEI, card, OXXO for fees |
| Notification Service | Status updates via WhatsApp/SMS |

### P2 - Medium

| System | Purpose |
|--------|---------|
| Professional Verification | Notary license, lawyer cédula |
| Batch Processing API | For high-volume users |

---

## 6. Conversation Design

### Dual-Track Approach

**For Citizens:**
- Explanatory tone
- Define terms (gravamen = lien, folio = property ID)
- Guide through decisions
- Proactive help

**For Professionals:**
- Efficient, concise
- Skip explanations
- Batch operations
- Direct system access

### Certificate Type Selection

```
Bot: "El Registro Público ofrece 8 tipos de certificados.
     El más común es el Certificado de Libertad de Gravamen,
     que muestra si tu propiedad tiene adeudos o hipotecas.

     ¿Para qué necesitas el certificado?

     1. Vender mi propiedad
     2. Solicitar un crédito/hipoteca
     3. Verificar estatus legal
     4. Trámite de herencia
     5. No estoy seguro"
```

### Folio Real Helper

```
User: "No sé cuál es mi folio real"

Bot: "El folio real es el número único de tu propiedad
     en el Registro Público.

     Puedo ayudarte a encontrarlo de 2 formas:

     1. Con tu número catastral (está en tu predial)
     2. Con la dirección exacta de la propiedad

     ¿Cuál tienes disponible?"
```

---

## 7. Knowledge Base Requirements

### 8 Certificate Types

| Certificate | Cost (UMAs) | Use Case |
|-------------|-------------|----------|
| Libertad de Gravamen | 4.5 UMA | Verify no liens |
| Existencia/Inexistencia | 3.0 UMA | Verify property exists |
| Inscripción | 3.5 UMA | Proof of registration |
| Antecedentes | 6.0 UMA | Full ownership history |
| No Propiedad | 3.0 UMA | Prove person doesn't own |
| Certificación de Documentos | 2.5 UMA | Certified copies |
| Constancia de Vigencia | 2.0 UMA | Current status |
| Certificación de Firmas | 1.5 UMA | Signature verification |

*Note: UMA 2026 = ~$113 MXN (update from INEGI)*

### Subdirection Coverage

| Subdirection | Coverage Area |
|--------------|---------------|
| Querétaro Centro | Centro, Norte |
| Querétaro Sur | Sur, Poniente |
| San Juan del Río | SJR municipality |
| Tequisquiapan | Tequisquiapan, Ezequiel Montes |
| Cadereyta | Cadereyta, Peñamiller |
| Jalpan | Sierra Gorda region |

### Common FAQs

- ¿Qué es el folio real?
- ¿Qué es un gravamen?
- ¿Cuánto tarda un certificado?
- ¿Puedo tramitar en línea?
- ¿Qué es CERLIN?
- ¿Cómo me registro en Alerta Registral?

---

## 8. Escalation Scenarios

### Immediate Escalation

| Trigger | Action |
|---------|--------|
| Complex legal (inheritance, judicial) | Human + lawyer referral |
| Multiple rejections | Human review |
| Fraud/unauthorized movement alert | Priority escalation |
| Payment disputes | Finance team |

### Standard Escalation

| Issue | Handling |
|-------|----------|
| CERLIN account issues | Technical support |
| Certificate status delays | Status investigation |
| Document requirements | Human clarification |

---

## Implementation Phases

### Phase 1 (Weeks 1-2)
- [ ] Certificate type selector
- [ ] Basic information responses
- [ ] Folio lookup guidance

### Phase 2 (Weeks 3-4)
- [ ] CERLIN registration guide
- [ ] Status tracking (manual)
- [ ] FAQ knowledge base

### Phase 3 (Weeks 5-8)
- [ ] ConsultasSire integration
- [ ] CERLIN API integration
- [ ] Payment integration

### Phase 4 (Weeks 9-12)
- [ ] Professional features
- [ ] Batch processing
- [ ] Alerta Registral enrollment

---

## Success Metrics

| Metric | Current (Est.) | Target |
|--------|----------------|--------|
| Certificate selection accuracy | Unknown | >85% |
| First-contact resolution | ~40% | >65% |
| CERLIN registration completion | ~60% | >85% |
| Professional satisfaction | Unknown | >4.0/5 |

---

## Key Files Referenced

- `agents/registry-rpp/agent.py` - Current implementation
- `agents/registry-rpp/tools.py` - Certificate info, status check
- `agents/registry-rpp/prompts.py` - Full knowledge base
- `ARCHITECTURE.md` - Subcategory codes

---
*Research completed: 2026-02-04*
*Priority: 5/13 (Complex dual-audience)*
