# Transporte Publico AMEQ - Domain Research Analysis

## Executive Summary

Analysis of the Transport domain for Gobierno de Queretaro's AI chatbot transformation. Current system has high deflection rate (~80%) due to app redirects for basic queries.

---

## 1. Current Menu Flow for Transport Services

The existing system routes through these subcategories:
- **TRA-TAR-001 to TRA-NIN-001**: Preferential cards (Student, Elderly, Disabled, Child 3-6)
- **TRA-UNI-001**: UNIDOS tariff ($2 fare program)
- **TRA-SAL-001/TRA-HIS-001**: Balance/history checks (redirects to QROBUS app)
- **TRA-RUT-001/TRA-MAP-001**: Route planning (app redirect + static PDF maps)
- **TRA-PER-001 to TRA-VEH-001**: Professional operator permits via IQT catalog

Current responses are static text with links to external resources.

---

## 2. User Journey Mapping

### Card Application Journey
- Currently requires in-person visit to single AMEQ office (Constituyentes No. 20)
- No appointment system
- Document requirements often unclear leading to rejected applications

### Balance Check Journey
- Requires downloading QROBUS app
- Manual navigation through app menus
- No direct chatbot support

### Route Planning Journey
- No direct route answers
- Users redirected to app
- Static PDF maps outdated

**Enhanced AI journeys would provide direct answers through API integration.**

---

## 3. Pain Points Identified

### Critical Issues
1. **App redirects for basic queries** (balance, routes)
2. **No real-time route/bus arrival information**
3. **UNIDOS tariff uncertainty** (follow social media for announcements)
4. **Single physical location** for card processing
5. **No appointment system** for office visits

### User Experience Gaps
- No indigenous language support (Otomi communities)
- Digital literacy barriers for elderly
- No proactive notifications
- Inconsistent information across channels

---

## 4. AI Enhancement Opportunities

### NLU Improvements
- Enhanced intent taxonomy for cards, routes, fares, reports
- Entity Extraction: Card numbers, route numbers, locations, times

### QROBUS API Integration
- Direct balance/history queries
- Card status checks

### Conversational Route Planning
- Natural language origin/destination
- Formatted multi-leg journey responses

### Proactive Engagement
- Low balance alerts
- Card expiry reminders
- Service disruption notifications

---

## 5. Required Integrations

### QROBUS System (Critical Priority)
```
GET /cards/{card_number}/balance
GET /cards/{card_number}/history
POST /cards/{card_number}/block
```

### IQT Route System (High Priority)
- GTFS data export for routes
- GTFS-RT for real-time updates
- Geocoding service for location resolution

### Shared Services
- Identity Service (CURP validation)
- Appointment System (AMEQ office scheduling)
- Notification Service (proactive alerts)
- CRM/Ticketing (complaint tracking)

---

## 6. Conversation Design for Special Populations

### Elderly Users
- Slower pace, simpler vocabulary
- Voice channel priority
- Step-by-step confirmations
- Family assistance option

### Students
- Quick, direct responses
- Mobile-friendly formatting
- Seasonal awareness (enrollment periods, renewals)

### Persons with Disabilities
- Clear, structured responses
- DIF credential requirement clearly explained
- Accessibility features highlighted

### Low-Income (UNIDOS)
- Dignified, non-judgmental language
- Proactive notification when programs open
- Simple enrollment guidance

---

## 7. Knowledge Base Requirements

### Static Knowledge
- Office locations, hours, contact info
- Fare structures (regular, preferential, UNIDOS)
- Card requirements per type
- Route maps (L53-LC23)
- External links (QROBUS app, IQT catalog, social media)
- FAQs (20+ common questions)

### Dynamic Knowledge (API-dependent)
- Real-time card balance
- Transaction history
- Bus arrival times
- Service alerts
- Program availability (UNIDOS convocatoria)

---

## 8. Escalation Scenarios

### Trigger Matrix

| Trigger | Level | Target | SLA |
|---------|-------|--------|-----|
| Human agent request | Immediate | Live queue | <5 min |
| Driver complaint | High | AMEQ Supervision | 24h |
| Safety incident | Critical | IQT + Authorities | Immediate |
| Card dispute | Medium | AMEQ Billing | 48h |
| Accessibility issue | High | AMEQ Operations | 24h |

### Handoff Protocol
- Context transfer with conversation ID, summary, entities
- Warm handoff message to both user and agent
- Fallback options when agents unavailable

---

## Implementation Priority

| Priority | Enhancement | Impact | Effort |
|----------|-------------|--------|--------|
| **P0** | QROBUS API Integration | High | Medium |
| **P1** | Natural Language Route Planning | High | High |
| **P1** | Document Checklist Generator | Medium | Low |
| **P2** | Appointment Scheduling System | Medium | Medium |
| **P3** | Proactive Notifications | High | High |

---

## Key Files Referenced

- `agents/transport-ameq/agent.py` - LangGraph agent definition
- `agents/transport-ameq/tools.py` - Domain tools
- `agents/transport-ameq/prompts.py` - Knowledge base from dumb-bot
- `ARCHITECTURE.md` - System architecture and subcategory codes

---
*Research completed: 2026-02-04*
