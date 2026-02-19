# Sensitive Services Protocol Guide

## Overview

Three services require special handling due to the vulnerable populations they serve:
1. **Atención Psicológica (SEJUVE)** - Mental health crisis
2. **Atención a Mujeres (IQM)** - Domestic violence
3. **Programas Sociales (SEDESOQ)** - Economic vulnerability

---

## 1. Mental Health Services (SEJUVE) Protocol

### Risk Categories

#### Level 1 - Information Seeking
- General inquiries about services
- Scheduling appointments
- Resource requests
**Handling**: Standard conversational flow with empathetic tone

#### Level 2 - Emotional Distress
- Expressing sadness, anxiety, stress
- Relationship or work problems
- Life transitions
**Handling**: Acknowledge feelings, offer resources, suggest professional support

#### Level 3 - Crisis (Non-Imminent)
- Recent loss or trauma
- Significant life crisis
- Prolonged depression/anxiety
**Handling**: Validate experience, prioritize appointment, provide hotline

#### Level 4 - Imminent Risk
- Suicidal ideation or plan
- Self-harm statements
- Psychotic symptoms
**Handling**: IMMEDIATE escalation to crisis line/emergency services

### Keyword Detection

```yaml
high_risk_keywords:
  suicide_related:
    - "quiero morirme"
    - "no quiero vivir"
    - "suicidio"
    - "quitarme la vida"
    - "terminar con todo"
    - "ya no aguanto más"
    - "nadie me extrañaría"
    - "sería mejor si no existiera"

  self_harm:
    - "cortarme"
    - "hacerme daño"
    - "lastimarme"
    - "golpearme"

  crisis_indicators:
    - "no tengo salida"
    - "no hay esperanza"
    - "todo es mi culpa"
    - "soy una carga"

  action: immediate_escalation
```

### Crisis Response Script

```
[On detecting high-risk keywords]

Bot: Me preocupa lo que me estás compartiendo.
Bot: Tu vida es valiosa y hay personas que pueden ayudarte ahora mismo.

Bot: Por favor, llama a la Línea de la Vida: 800 911 2000
Bot: Está disponible las 24 horas, los 7 días de la semana.

Bot: También puedes llamar al 911 si necesitas ayuda inmediata.

Bot: ¿Hay alguien de confianza que pueda estar contigo en este momento?

[Wait for response, maintain connection]

Bot: Quiero que sepas que buscar ayuda es un acto de valentía.
Bot: ¿Te gustaría que te ayude a contactar a alguien?
```

### Data Privacy

- Conversations may be anonymized unless emergency
- No message history stored by default (user can opt-in)
- Clinician access to context upon escalation only
- Mandatory reporting for minors in danger

---

## 2. Women's Services (IQM) Protocol

### Safety-First Design

#### Discrete Interface
- No "violence" words in visible menus
- Quick exit button ("Salir rápido")
- Fake website redirect option
- No persistent notifications
- Option to disable chat history

#### Code Word System
```yaml
code_words:
  - "pizza": Need help but can't talk openly
  - "medicina": Abuser is present
  - "llueve": Send emergency contact

  response:
    "pizza":
      Bot: "Entendido. ¿Puedes contestar sí o no?"
      Bot: "¿Estás en peligro ahora mismo?"
    "medicina":
      Bot: "Entiendo. Voy a darte información como si fuera otra cosa."
      Bot: "Te mando el 'horario de la farmacia': [shelter info disguised]"
```

### Danger Assessment

```yaml
assessment_questions:
  - "¿Tienes miedo de tu pareja o alguien en tu casa?"
  - "¿Te han amenazado con hacerte daño a ti o a tus hijos?"
  - "¿Han usado armas o te han golpeado?"
  - "¿Has tenido que ir al hospital por golpes?"
  - "¿Controlan tu dinero, teléfono o con quién hablas?"

scoring:
  3+ yes: High risk - immediate safety planning
  1-2 yes: Medium risk - connect with advocate
  0 yes: Information seeking - provide resources
```

### Safety Planning Conversation

```
Bot: Tu seguridad es lo primero. Vamos a hacer un plan juntas.

Bot: ¿Tienes un lugar seguro donde puedas ir si necesitas salir rápido?
[Capture response]

Bot: ¿Hay alguna persona de confianza que pueda ayudarte?
[Capture response]

Bot: ¿Tienes documentos importantes accesibles (identificación, actas)?
[If no: provide guidance on obtaining copies]

Bot: ¿Tienes acceso a algo de dinero que él no controle?
[Provide resources for financial assistance]

Bot: Te voy a compartir el número de Tel Mujer: 442 216 4757
Bot: Está disponible las 24 horas.
Bot: Puedes guardarlo como contacto de "farmacia" o "trabajo".
```

### Escalation Paths

1. **Information only** → Resource delivery, follow-up offer
2. **Emotional support** → Counseling appointment
3. **Active planning** → Advocate connection, shelter info
4. **Immediate danger** → 911, safe house direct transfer

---

## 3. Social Programs (SEDESOQ) Protocol

### Dignity-Preserving Language

#### DO:
- "Este programa está diseñado para apoyarte"
- "Tienes derecho a estos beneficios"
- "Estamos aquí para ayudarte"

#### DON'T:
- "Beneficencia" / "caridad"
- "Los pobres" / "necesitados"
- Language implying judgment

### Accessibility Considerations

```yaml
accessibility:
  low_literacy:
    - Use simple, short sentences
    - Avoid bureaucratic terms
    - Offer voice messages
    - Use visual guides where possible

  limited_connectivity:
    - SMS fallback available
    - Offline info packets
    - Low-bandwidth mode

  elderly_users:
    - Larger text option
    - Slower pace
    - Repeat confirmation
    - Family member assistance option

  indigenous_communities:
    - Otomí language support
    - Cultural sensitivity
    - Community liaison contact
```

### Fraud Prevention (Without Accusation)

```
[Instead of requiring excessive documentation upfront]

Bot: Para verificar tu información, necesito hacerte algunas preguntas.
Bot: Esto es para proteger el programa y asegurar que llegue a quien lo necesita.

[Ask verification questions conversationally]

Bot: ¿Me puedes confirmar tu dirección?
Bot: ¿Cuántas personas viven en tu hogar?
Bot: ¿Algún miembro ya recibe este apoyo?

[Flag inconsistencies for human review, don't accuse]
```

### Proactive Renewal Support

```yaml
renewal_flow:
  90_days_before:
    notification: "Tu beneficio de [program] se renueva en 3 meses."
    action: "¿Quieres comenzar el proceso ahora?"

  60_days_before:
    notification: "Recordatorio: Tu beneficio necesita renovarse."
    action: "¿Necesitas ayuda con los documentos?"

  30_days_before:
    notification: "IMPORTANTE: Solo quedan 30 días para renovar."
    action: "Agenda cita ahora para evitar perder tu beneficio."

  7_days_before:
    notification: "URGENTE: Tu beneficio expira en 7 días."
    action: "Llama a este número para asistencia inmediata: [number]"
```

---

## Universal Sensitive Data Handling

### Data Classification

```yaml
sensitivity_levels:
  public:
    - Office locations
    - Service hours
    - General requirements

  confidential:
    - Citizen CURP
    - Contact information
    - Case numbers

  highly_sensitive:
    - Mental health conversations
    - Domestic violence reports
    - Income/poverty status
    - Family composition

  restricted:
    - Crisis intervention logs
    - Abuse allegations
    - Medical information
```

### Access Controls

- **Level 1 (Bot)**: Public + basic confidential
- **Level 2 (Agent)**: All confidential, case-specific sensitive
- **Level 3 (Supervisor)**: All sensitive within domain
- **Level 4 (Admin)**: Full access with audit

### Audit Requirements

All access to sensitive data must log:
- Who accessed
- When accessed
- What was accessed
- Why (purpose code)
- From where (channel/device)

### Data Retention

```yaml
retention:
  standard_conversations: 90 days
  case_related: 5 years
  crisis_interventions: 10 years
  anonymous_analytics: indefinite

  right_to_delete:
    - Upon citizen request
    - Exceptions: active cases, legal holds
```

---

## Training Requirements

### All Staff
- Sensitivity and dignity training
- Privacy compliance
- Basic crisis recognition

### Crisis Service Staff
- Mental health first aid certification
- Domestic violence response training
- Suicide prevention training
- Trauma-informed care

### System Monitoring
- Real-time crisis detection alerts
- Supervisor notification for high-risk
- Quality assurance reviews
- Regular calibration sessions
