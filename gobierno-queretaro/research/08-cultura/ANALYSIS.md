# Cultura (Cultural Services) - Domain Research Analysis

## Executive Summary

Analysis of the Cultural Services domain for Gobierno de Queretaro's AI chatbot transformation. Current system provides static information about 13 cultural venues with basic details. Priority 12 of 13 (lower volume) but high implementation ease.

---

## 1. Current Menu Flow Analysis

The existing culture agent provides static information:

### Main Menu Structure
- **Centros Culturales y Museos** (13 venues)
- **Cartelera Cultural** (external link)
- **Programa "La Cultura esta en Nosotros"** (PDF link)
- **Contacto** information

### 13 Cultural Venues Covered
1. Museo Regional de Querétaro
2. Museo de Arte de Querétaro
3. Museo de la Ciudad
4. Museo de la Restauración de la República
5. Casa de la Zacatecana
6. Galería Libertad
7. Centro Cultural Gómez Morín
8. Casa de Cultura de Querétaro
9. Teatro de la República
10. Centro de las Artes de Querétaro
11. Casa del Faldón
12. Museo de los Conspiradores
13. Museo del Calendario

### Current Response Pattern
```
User: "¿Qué museos hay?"
Bot: [Static list of venues with hours and addresses]
```

---

## 2. User Journey Mapping

### Journey A: Event Discovery
**Current**: Leave chat → Search external website → High friction
**Enhanced**: "¿Qué hay este fin de semana?" → Filtered recommendations

### Journey B: Museum Visit Planning
**Current**: Static venue info, no recommendations
**Enhanced**: Personalized suggestions based on interests, time, group size

### Journey C: Workshop Enrollment
**Current**: No digital enrollment, manual tracking, double bookings
**Enhanced**: Real-time capacity, instant registration, automated reminders

### Journey D: Support Program Application
**Current**: Complex 20+ page PDF, high abandonment
**Enhanced**: Conversational eligibility check, guided document preparation

---

## 3. Pain Points Identified

### Event Discovery Friction
- External website required for current events
- No filtering by date, type, audience, or cost
- No personalized recommendations

### Workshop Enrollment Issues
- No digital enrollment system
- Manual tracking causes double bookings
- No capacity visibility
- No reminders

### Program Complexity
- "La Cultura esta en Nosotros" is 20+ page PDF
- High abandonment rate
- Complex eligibility requirements
- No guided application

### Information Gaps
- Only 13 venues, missing theaters, libraries, public spaces
- No real-time event calendar
- No ticket availability

---

## 4. AI Enhancement Opportunities

| Priority | Enhancement | Impact | Effort |
|----------|-------------|--------|--------|
| **P0** | Event Discovery with Filters | High | Medium |
| **P1** | Workshop Enrollment System | High | Medium |
| **P1** | Calendar Integration | High | Medium |
| **P2** | Guided Program Applications | Medium | High |
| **P2** | Multilingual Support (Tourism) | Medium | Medium |
| **P3** | Ticketing Integration | Medium | High |

### Event Discovery & Recommendations
- Semantic search: "algo para niños este sábado"
- Filters: date, event type, audience, cost, location
- Personalized based on past interests

### Workshop Enrollment System
- Real-time capacity checking
- Instant registration
- Automated reminders
- Waitlist management

### Calendar Integration
- Dynamic event data vs static links
- Weekly highlights
- Upcoming deadlines

---

## 5. Required Integrations

| System | Purpose | Priority |
|--------|---------|----------|
| Event Calendar API | Real-time event data | **Critical** |
| Ticketing System | Availability and purchase | High |
| Workshop Management | Enrollment and capacity | High |
| Support Program Portal | Applications and status | Medium |
| Notification Service | Reminders and updates | High |

---

## 6. Conversation Design Recommendations

### Tone Guidelines
- **Enthusiastic** but not overwhelming
- **Accessible** - avoid elitist art jargon
- **Local** - use Queretaro references
- **Inclusive** - all ages, backgrounds welcome

### Cultural Intents (15+ mapped)

**Discovery Intents:**
- `culture.events.search` - Find events
- `culture.events.this_weekend` - Weekend activities
- `culture.venue.info` - Venue details
- `culture.venue.hours` - Operating hours
- `culture.recommend` - Get recommendations

**Transaction Intents:**
- `culture.workshop.enroll` - Register for workshop
- `culture.workshop.cancel` - Cancel registration
- `culture.tickets.buy` - Purchase tickets
- `culture.program.apply` - Apply for support program

### Sample Conversation Flow

```
User: "¿Qué hay para hacer con niños este fin de semana?"

Bot: "¡Excelente idea para un paseo familiar! 🎨 Este fin de semana hay:

📍 Museo de Arte de Querétaro
   • Taller infantil de pintura - Sábado 11:00
   • Entrada libre para menores de 12

📍 Centro de las Artes
   • Obra de teatro infantil - Domingo 12:00
   • Boletos: $50 MXN

¿Te interesa alguna de estas opciones?"
```

---

## 7. Knowledge Base Requirements

### Static Knowledge (Expand)
- **Current**: 13 venues
- **Needed**: Add theaters, libraries, public art spaces, festivals
- Venue details: hours, cost, accessibility, parking
- Historical context and highlights

### Dynamic Knowledge (API Integration)
- Real-time event calendar
- Workshop schedules and capacity
- Program deadlines and requirements
- Ticket availability

### FAQ Bank (50+ questions)
- General: costs, hours, accessibility
- Events: how to find, how to attend
- Workshops: how to enroll, requirements
- Programs: eligibility, application process

---

## 8. Escalation Scenarios

### Immediate Escalation
| Trigger | Action |
|---------|--------|
| Complaints about service | Human agent |
| Safety incidents | Security + management |
| Discrimination reports | Human agent + documentation |
| VIP/press requests | Communications team |

### Scheduled Callback
- Complex program questions
- Venue rental inquiries
- Partnership proposals
- Large group visits

### Self-Service (AI Handles)
- Event lookups
- Venue information
- Basic workshop enrollment
- FAQ responses

---

## Priority Assessment

| Factor | Score | Notes |
|--------|-------|-------|
| User Volume | 4/10 | Lower than core services |
| Current Pain | 4/10 | Functional but limited |
| Impact Potential | 6/10 | Cultural engagement driver |
| Implementation Ease | 7/10 | Less regulatory complexity |
| **Overall Priority** | **12/13** | Lower priority but quick wins |

---

## Implementation Phases

### Phase 1 (Months 1-2)
- Enhanced venue search
- Event discovery (if calendar API available)
- FAQ improvements

### Phase 2 (Months 2-3)
- Workshop enrollment system
- Notification integration
- User preference tracking

### Phase 3 (Months 3-4)
- Ticketing integration (if system available)
- Personalized recommendations
- Guided program applications

### Phase 4 (Ongoing)
- Virtual tours
- Audio descriptions (accessibility)
- Multilingual support (tourism)

---

## Key Files Referenced

- `agents/culture/prompts.py` - Full knowledge base
- `agents/culture/tools.py` - 5 tools with mock data
- `agents/culture/agent.py` - LangGraph agent implementation

---
*Research completed: 2026-02-04*
