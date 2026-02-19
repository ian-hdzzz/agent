# Atención Psicológica SEJUVE - Domain Research Analysis

## Executive Summary

**CRITICAL: This is a SENSITIVE SERVICE involving mental health. Crisis protocols are mandatory.**

Analysis of the Psychological Services (SEJUVE) domain for Gobierno de Queretaro's AI chatbot transformation. Current system has a single flat menu option with no crisis detection capability.

---

## 1. Current Menu Flow Analysis

The existing bot has a single flat menu option (PSI-ATE-001) with critical limitations:
- No differentiation between information seekers and crisis situations
- No crisis detection capability
- Manual handoff only, causing delays
- No after-hours guidance
- Limited service information

### Current Response Pattern
```
User: "Necesito ayuda psicológica"
Bot: [Static info about SEJUVE services] + [Phone number]
```

**This is insufficient for mental health services.**

---

## 2. User Journey Mapping

### Journey A: Information Seeker
- Needs service overview and eligibility info
- Questions about cost, confidentiality, wait times
- AI can handle autonomously

### Journey B: Appointment Request
- Needs scheduling workflow
- Availability checking
- Requires human review before confirmation

### Journey C: User in Distress (Non-Crisis)
- Needs empathetic response and resources
- Self-help tools and grounding techniques
- Warm handoff to services

### Journey D: CRISIS ⚠️
- **Requires IMMEDIATE escalation**
- Linea de la Vida: **800-911-2000**
- Never leave user alone
- Document everything

### Journey E: Third Party Inquiry
- Family/friends seeking help for someone
- Resources for supporting others
- How to encourage help-seeking

---

## 3. Pain Points Identified

### Stigma Barriers
- Social stigma around mental health
- Self-stigma ("I should handle this alone")
- Lack of awareness about available services

### Access Issues
- Limited hours (L-V 9:00-17:00)
- Unknown wait times
- Physical location required for services
- No after-hours support pathway

### Youth-Specific Challenges
- School pressure and academic stress
- Identity formation struggles
- Peer relationships and bullying
- Social media impact on mental health

---

## 4. AI Enhancement Opportunities

### Pre-Clinical Screening Tool
"Check-In Emocional" - anonymous self-assessment
- Not diagnostic, but identifies need level
- Routes appropriately based on responses

### Intelligent Appointment Booking
- Real-time availability checking
- Preference matching (gender, specialty)
- Automatic reminders

### Self-Help Resource Library
- Anxiety management techniques
- Stress reduction exercises
- Sleep hygiene guides
- Grounding exercises for acute distress

### Proactive Check-Ins
- Post-appointment follow-up
- Between-session support
- Appointment reminders with encouragement

---

## 5. Required Integrations

| System | Purpose | Priority |
|--------|---------|----------|
| SEJUVE Calendar | Appointment scheduling | High |
| Case Management | Session tracking | Medium |
| Staff Notifications | **CRITICAL for crisis** | **Critical** |
| External Crisis Lines | Linea de la Vida, SAPTEL | **Critical** |

---

## 6. Conversation Design for Mental Health

### Tone Guidelines
- **Warm** but not overly casual
- **Non-judgmental** - no "you should" statements
- **Validating** - acknowledge feelings before providing info
- **Hopeful** but realistic
- **Clear** - mental health topics can be confusing

### Response Templates

**Warm Greeting:**
```
"Hola, gracias por escribir. Estoy aquí para ayudarte a conocer
los servicios de apoyo psicológico disponibles. ¿Cómo te puedo apoyar hoy?"
```

**Empathy Response:**
```
"Entiendo que puede ser difícil dar este paso. Es muy valiente
buscar apoyo. Estoy aquí para ayudarte."
```

**Service Information:**
```
"El programa Ser Tranquilidad de SEJUVE ofrece atención psicológica
gratuita y confidencial para jóvenes de 12 a 29 años."
```

---

## 7. CRISIS DETECTION AND ESCALATION ⚠️

### Three-Tier Keyword Detection

**Tier 1 - IMMEDIATE (Red Alert)**
- "quiero morirme", "me quiero matar"
- "suicidio", "suicidarme"
- "cortarme", "hacerme daño"
- "no quiero vivir", "mejor muerto"
- "tengo un plan para..."

**Tier 2 - URGENT (Orange Alert)**
- Passive ideation: "ojalá no despertara"
- Hopelessness: "nada tiene sentido"
- Severe isolation: "nadie me extrañaría"

**Tier 3 - ELEVATED (Yellow Alert)**
- Distress indicators requiring monitoring
- "me siento muy mal", "no puedo más"
- Recent loss or trauma mentioned

### Crisis Response Protocol

```
1. ACKNOWLEDGE immediately - "Gracias por compartir esto conmigo"
2. PROVIDE CRISIS LINE IMMEDIATELY:

   ⚠️ LINEA DE LA VIDA: 800-911-2000 (24/7, Gratuita)

3. EMERGENCY BACKUP: "Si estás en peligro inmediato, llama al 911"
4. SAFETY CHECK: "¿Estás en un lugar seguro ahora?"
5. SUPPORT CHECK: "¿Hay alguien contigo o que pueda estar contigo?"
6. MAINTAIN CONNECTION: Stay engaged until help arrives
7. HUMAN ESCALATION: Alert staff immediately
8. DOCUMENTATION: Log entire interaction
```

### Crisis Line Quick Reference

| Resource | Number | Availability |
|----------|--------|--------------|
| **Linea de la Vida** | **800-911-2000** | **24/7, Gratuita** |
| SAPTEL | 55-5259-8121 | 24/7 |
| Emergencias | 911 | 24/7 |
| Linea Joven SEJUVE | 442-214-2700 | L-V 9:00-17:00 |

---

## 8. Knowledge Base Requirements

### Ser Tranquilidad Program Details
- **Eligibility**: 12-29 years old
- **Cost**: Free (Gratuito)
- **Confidentiality**: Yes, with mandatory reporting exceptions
- **Services**: Individual therapy, group therapy, family orientation, workshops

### FAQs
- Is it confidential? (Yes, with exceptions for safety)
- How much does it cost? (Free)
- How long is the wait? (Varies, typically 1-2 weeks)
- Can I request a specific therapist gender? (Yes)

### Psychoeducation Resources
- Grounding techniques (5-4-3-2-1 method)
- Breathing exercises (box breathing)
- Sleep hygiene basics
- When to seek help guide

---

## 9. Mandatory Human Oversight Requirements

### Three-Level Oversight Model

| Level | Scenario | AI Role | Human Role |
|-------|----------|---------|------------|
| 1 | General information | Autonomous | Review logs |
| 2 | Appointments/Intake | Assisted | Review before confirm |
| 3 | ANY crisis indicator | Immediate escalation | **Take over** |

### Supervision Requirements
- **Real-time monitoring** of active conversations
- **Quality review** of all mental health interactions
- **Training** on mental health conversation handling
- **Documentation** of all escalations and outcomes

---

## Critical Recommendations

1. **Safety First**: Crisis detection must be 99%+ accurate. Any missed escalation is unacceptable.

2. **Human Oversight is Non-Negotiable**: AI augments, never replaces, clinical judgment.

3. **Clear Boundaries**: AI provides information and connection, not therapy.

4. **24/7 Crisis Resources**: After-hours protocol must ALWAYS provide Linea de la Vida (800-911-2000).

5. **Continuous Improvement**: Mental health language evolves; regular keyword list updates essential.

---

## Key Files Referenced

- `agents/psychology-sejuve/prompts.py` - Existing prompts and knowledge base
- `agents/psychology-sejuve/tools.py` - Domain tools including crisis resources
- `agents/psychology-sejuve/agent.py` - LangGraph agent implementation
- `research/synthesis/SENSITIVE_SERVICES_PROTOCOLS.md` - Existing crisis protocols

---
*Research completed: 2026-02-04*
*⚠️ SENSITIVE SERVICE - Handle with care*
