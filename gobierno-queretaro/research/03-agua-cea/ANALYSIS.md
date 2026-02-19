# Servicios de Agua CEA - Domain Research Analysis

## Executive Summary

Analysis of the Water Services (CEA) domain for Gobierno de Queretaro's AI chatbot transformation. The existing system has a well-structured AGORA classification with 7 main categories and 60+ subcategories. SOAP API integration is already functional.

---

## 1. Current Menu Flow for Water Services

The existing system uses AGORA classification:

### Main Categories
| Code | Category | Description |
|------|----------|-------------|
| CON | Consultas | General inquiries, balance queries, office information |
| FAC | Facturación | Receipts, billing clarifications, payment options |
| CTR | Contratos | New connections, titular changes, rate modifications |
| CVN | Convenios | Payment plans for seniors, disabled, pensioners |
| REP | Reportes | Leaks, drainage, water quality issues (14 subcategories) |
| SRV | Servicios Técnicos | Meters, installations, technical work |
| CNS | Consumos | Consumption history and trends |

**Total: 60+ subcategories mapped**

---

## 2. User Journey Mapping

### Bill Inquiry Journey
```
Contract request -> SOAP API query -> Formatted response with follow-up
```
- Multi-contract support needed
- Payment options presented after balance shown

### Leak Report Journey
```
Location -> Photo evidence -> Severity check -> Ticket creation
```
- **CRITICAL**: NO contract required for public street issues
- Photo evidence optional but encouraged
- Real-time ticket status updates needed

### Payment Plan Journey
```
Debt assessment -> Plan type determination -> Requirements -> Office formalization
```
- Special programs for seniors, disabled, pensioners (CVN)
- In-person requirement for plan formalization

### New Connection Journey
```
Immediate handoff to human agent
```
- **CRITICAL RULE**: Always escalate CTR-001, CTR-002

---

## 3. Pain Points Identified

### Technical Issues
- SOAP API latency (2-5 seconds)
- Proxy requirement for CEA API access
- XML parsing complexity

### User Experience Issues
- Multiple questions required for simple tasks
- Technical codes exposed to users (**NEVER mention codes**)
- Photo evidence requests inconsistent

### Business Process Issues
- Manual ticket creation overhead
- In-person requirement for payment plans
- Unclear escalation criteria

---

## 4. AI Enhancement Opportunities

### Bill Lookup Enhancements
- Multi-contract management dashboard
- Proactive payment due notifications
- Payment history analytics

### Leak Reporting Enhancements
- Geolocation integration for precise location
- Image analysis for severity assessment
- Real-time crew dispatch status

### Payment Integration
- In-chat payment processing
- Automated payment plan enrollment
- CoDi/SPEI payment links

### Consumption Analytics
- Predictive modeling for bills
- Anomaly detection (leak indicators)
- Conservation recommendations

---

## 5. Required Integrations

### Existing Integrations (Functional)
```
CEA SOAP APIs: https://aquacis-cf.ceaqueretaro.gob.mx
- Debt lookup
- Consumption history
- Contract information
- WS-Security authentication
```

### Proposed Integrations
- **Payment Gateway**: SPEI, CoDi, OXXO Pay
- **Geolocation Service**: For leak reporting accuracy
- **Notification Service**: WhatsApp, SMS, Email proactive alerts
- **PostgreSQL/Chatwoot**: Ticket management (existing)

---

## 6. Conversation Design Recommendations

### Critical Rules
1. **Maximum 2-3 sentences per response**
2. **ONE question per message**
3. **NEVER mention internal codes** (FAC-004, REP-FVP, etc.)
4. **Use formatted_response exactly** as provided by tools
5. **Immediate handoff** for new service requests and billing clarifications

### Response Formatting
```
✅ Good: "Tu saldo es de $245.00 MXN. ¿Deseas conocer las opciones de pago?"
❌ Bad: "He consultado el sistema FAC-001 y tu saldo según el código de respuesta es..."
```

### Empathy for Payment Difficulties
- Acknowledge financial stress without judgment
- Proactively mention payment plan options
- Provide clear next steps

---

## 7. Knowledge Base Requirements

### Static Content
- Office locations, hours, services by location
- Payment methods and physical payment locations
- Document requirements per service type
- Tariff structures and rate categories
- Support programs (seniors, disabled, pensioners)

### Dynamic Content (API-driven)
- Real-time balance and consumption
- Contract status and details
- Active ticket status updates
- Payment confirmation

---

## 8. Escalation Scenarios

### Immediate Escalation Triggers
| Trigger | Action |
|---------|--------|
| User requests human agent | Transfer immediately |
| New service requests (CTR-001, CTR-002) | Mandatory handoff |
| Billing clarifications (FAC-004) | Mandatory handoff |
| Billing adjustments (FAC-005) | Mandatory handoff |
| User frustration detected | Offer human agent |
| Ticket closure requests | Only agents can close |

### Emergency Escalation
- Major water main breaks → Emergency dispatch
- Sewage overflow → Health hazard protocol
- Complete service outage → Priority response
- Water contamination reports → Immediate investigation

---

## Implementation Status

### Completed ✅
- SOAP API integration with retry mechanisms
- Skill-based classification (7 categories)
- Ticket creation and Chatwoot integration
- Formatted response templates

### Recommended Next Steps
| Timeline | Enhancement |
|----------|-------------|
| Q1 2026 | Payment gateway for in-chat transactions |
| Q1 2026 | Geolocation for improved leak reporting |
| Q2 2026 | Proactive consumption notifications |
| Q2 2026 | Predictive analytics for conservation |

---

## Key Files Referenced

- `gobierno-queretaro/agents/water-cea/agent.py` - LangGraph agent
- `gobierno-queretaro/agents/water-cea/tools.py` - SOAP API integrations
- `gobierno-queretaro/agents/water-cea/prompts.py` - Skill-specific prompts
- `maria-claude/src/tools.ts` - Native Claude Agent SDK tools
- `maria-claude/src/skills/*.ts` - All 7 skill definitions
- `maria-claude/MARIA_DOCUMENTATION.md` - Complete documentation

---
*Research completed: 2026-02-04*
