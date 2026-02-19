# Trámites Vehiculares (Vehicle Services) - Domain Research Analysis

## Executive Summary

**Priority 1 of 13** - Highest priority for implementation due to high user volume and significant impact potential.

Analysis of the Vehicle Services domain for Gobierno de Queretaro's AI chatbot transformation. Covers vehicle registration, tenencia (vehicle tax), license plates, verification, and related financial services administered by the Secretaria de Finanzas.

| Factor | Score |
|--------|-------|
| User Volume | 9/10 |
| Impact Potential | 8/10 |
| Implementation Ease | 8/10 |

---

## 1. Current Menu Flow Analysis

The existing dumb-bot handles 8 service categories:

| Code | Service | Current Behavior |
|------|---------|------------------|
| VEH-TEN-001 | Pago de Tenencia | Link to portal |
| VEH-OFI-001 | Oficinas Recaudadoras | Static directory link |
| VEH-CON-001 | Consulta/Pago Portal Tributario | External redirect |
| VEH-COM-001 | Descarga Comprobante | Link only |
| VEH-FAQ-001 | Preguntas Frecuentes | Static responses |
| VEH-SUS-001 | Sustitución de Placa | Step-by-step text |
| VEH-DES-001 | Placas Desgastadas | Process info |
| VEH-INF-001 | Información General | Generic info |

### Key Limitations
- No real-time lookups (users must leave WhatsApp)
- Static content regardless of user situation
- No payment integration
- No context awareness between interactions
- No plate validation before portal redirect
- No deadline awareness or proactive reminders

---

## 2. User Journey Mapping

### Journey A: Tenencia Payment
**Current**: 7-10 steps with browser switching
**Enhanced**: 3-4 steps with in-chat payment

```
Current Flow:
User → Menu → Link → Browser → Portal → Search → Pay → Return

Enhanced Flow:
User: "Cuánto debo de tenencia? QRO-123-A"
Bot: "Tu adeudo es $2,450. ¿Deseas pagar ahora?"
User: "Sí"
Bot: [Payment link] → Confirmation → Receipt
```

### Journey B: Plate Replacement (Lost/Stolen)
**Current**: Fragmented process, no Fiscalía guidance
**Enhanced**: Guided flow with locations and appointments

### Journey C: Vehicle Verification
**Current**: Generic calendar
**Enhanced**: Personalized schedule based on plate ending

### Journey D: New Vehicle Registration
**Current**: Static requirements list
**Enhanced**: Conditional guidance with cost estimation

### Journey E: Change of Ownership
**Current**: No debt verification
**Enhanced**: Integrated debt check + payment before transfer

---

## 3. Pain Points Identified

### Payment Complexity
- Multiple confusing portals (tenencia.queretaro.gob.mx vs portal-tributario)
- External browser required causing drop-off
- No payment confirmation in WhatsApp
- No receipt delivery in conversation

### Document Requirements
- Generic lists don't adapt to user situation
- No format guidance leading to rejected applications
- Fiscalía process unclear for plate replacement

### Service Discovery
- Menu-driven navigation is slow
- Keywords not intuitive
- No proactive recommendations

### Deadline Management
- No reminders for tenencia deadlines
- Users miss discount periods (January-March)
- Verification calendar confusing

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Impact | Effort |
|----------|-------------|--------|--------|
| **P0** | Intelligent Plate Lookup | High | Medium |
| **P0** | Payment Integration | High | High |
| **P1** | Appointment Scheduling | Medium | Medium |
| **P1** | Proactive Notifications | High | Medium |
| **P2** | Document Validation | Medium | Medium |
| **P2** | Multi-Vehicle Management | Medium | Low |

### Intelligent Plate Lookup
- Real-time debt query by plate
- Verification status check
- Registration validity
- Outstanding infractions

### Payment Integration
- Generate secure payment links
- Support: Card, SPEI, OXXO
- In-chat receipt delivery
- Payment confirmation webhooks

### Proactive Notifications
- Tenencia deadline reminders
- Discount period alerts (January)
- Verification due dates
- Registration expiry warnings

---

## 5. Required Integrations

### Critical Priority
| System | Purpose |
|--------|---------|
| **Portal Tributario API** | Vehicle lookup, debt query, payment generation |
| **Payment Gateway** (OpenPay/Conekta) | PCI-compliant card processing |

### High Priority
| System | Purpose |
|--------|---------|
| Appointment System | Slots query, booking, reminders |
| Notification Service | WhatsApp templates for confirmations |

### Medium Priority
| System | Purpose |
|--------|---------|
| Verification Centers Directory | Locations, hours, availability |
| Fiscalía Information | Office locations for police reports |

---

## 6. Conversation Design Recommendations

### Plate Format Validation
```
Queretaro plates: QRO-###-X or QQA-##-## (older)
Validate before API call to reduce errors
```

### Debt Presentation
```
Bot: "📋 Adeudo de vehículo QRO-123-A:

   Tenencia 2026: $2,450.00
   ✨ Descuento enero: -$245.00
   ────────────────
   Total a pagar: $2,205.00

   ⏰ El descuento vence el 31 de enero.

   ¿Deseas generar tu línea de pago?"
```

### Error Handling
```
Bot: "No encontré información para esa placa.
     Verifica que sea correcta (ejemplo: QRO-123-A).

     Si el problema continúa, puedo transferirte
     con un asesor. ¿Qué prefieres?"
```

---

## 7. Knowledge Base Requirements

### Tenencia Information
- 2026 deadlines and discount periods
- January: 10% discount
- February: 5% discount
- March: No discount, no penalty
- April+: Penalties apply
- Exemptions (disabled, seniors, hybrids)

### Office Directory
- All Recaudación offices
- Addresses, hours, phone numbers
- GPS coordinates for directions
- Services available per location

### Requirements Database
Conditional requirements for each trámite:
- New registration: invoice, ID, proof of address, payment
- Plate replacement: police report, ID, photos
- Change of ownership: both parties' IDs, sale contract, debt clearance

### Verification Calendar 2026
| Plate Ending | Verification Period |
|--------------|---------------------|
| 1, 2 | January-February |
| 3, 4 | March-April |
| 5, 6 | May-June |
| 7, 8 | July-August |
| 9, 0 | September-October |

---

## 8. Escalation Scenarios

### Automatic Triggers
| Trigger | Action |
|---------|--------|
| User requests human agent | Immediate transfer |
| 3 failed interaction attempts | Offer human assistance |
| Out-of-state vehicle detected | Transfer to agent |
| Disputed debt amount | Transfer to agent |
| Inheritance/deceased owner | Sensitive handling + transfer |

### Handoff Protocol
1. Collect: plate, issue nature, contact preference
2. Transfer: conversation context and sentiment
3. Provide: direct phone while waiting (442-238-5000)

---

## Implementation Timeline

### Phase 1 (Month 4)
- [ ] Tenencia lookup by plate
- [ ] Payment link generation
- [ ] Office directory
- [ ] Basic FAQ

### Phase 2 (Month 4-5)
- [ ] Verification calendar
- [ ] Document requirements
- [ ] Appointment scheduling
- [ ] Receipt download

### Phase 3 (Month 5-6)
- [ ] Multi-vehicle management
- [ ] Proactive notifications
- [ ] Payment webhooks
- [ ] Analytics dashboard

---

## Success Metrics

| Metric | Current | 6-Month Target |
|--------|---------|----------------|
| First Contact Resolution | ~20% | >65% |
| Average Handling Time | 8-10 min | <3 min |
| Portal Redirect Rate | 100% | <30% |
| User Satisfaction | N/A | >4.2/5 |
| Human Escalation | Unknown | <15% |

---

## Key Files Referenced

- `agents/vehicles/prompts.py` - Knowledge base
- `agents/vehicles/tools.py` - Portal integration stubs
- `agents/vehicles/agent.py` - LangGraph agent

---
*Research completed: 2026-02-04*
*Priority: 1/13 (Highest)*
