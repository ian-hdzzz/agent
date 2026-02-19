# Sensitive Services AI Best Practices
## Gobierno de Queretaro AI Platform - Research Document

**Research Date:** February 2026
**Applicable Domains:** Psicologia SEJUVE, Mujeres IQM, Conciliacion Laboral, SEDESOQ

---

## Executive Summary

This document synthesizes current best practices (2024-2026) for handling sensitive conversations in AI systems, specifically tailored for the four sensitive service domains within the Gobierno de Queretaro AI platform. The research draws from academic literature, regulatory frameworks, clinical guidelines, and real-world implementations of AI systems designed for vulnerable populations.

---

## 1. Crisis Detection Systems

### 1.1 Tiered Keyword System

Based on clinical pathways for managing suicide risk and the Columbia-Suicide Severity Rating Scale (C-SSRS), implement a three-tier detection system:

#### Tier 1: IMMEDIATE (Automatic Escalation)
**Response Time:** < 30 seconds to human handoff

Keywords and Patterns:
- Direct suicidal statements: "quiero morir," "me voy a matar," "no quiero vivir"
- Active plan indicators: "tengo pastillas," "ya tengo un plan," "esta noche"
- Violence in progress: "me esta golpeando," "esta aqui," "ayuda"
- Self-harm in progress: "me estoy cortando," "acabo de tomar"
- Homicidal ideation: "voy a matar," "lo voy a hacer"

**Action Protocol:**
1. Immediately display emergency resources (911, 800-290-0024 Linea de la Vida)
2. Trigger real-time human escalation
3. Do NOT continue conversational flow
4. Log interaction for safety review

#### Tier 2: URGENT (Expedited Human Review)
**Response Time:** < 5 minutes for human contact

Keywords and Patterns:
- Passive suicidal ideation: "seria mejor si no existiera," "todos estarian mejor sin mi"
- Recent crisis indicators: "hace dias que no duermo," "no he comido en dias"
- Escalating abuse: "cada vez es peor," "me amenaza de muerte"
- Severe distress: "no puedo mas," "estoy desesperado/a"
- Ambiguous death references: "pienso mucho en la muerte," "me pregunto como seria"

**Action Protocol:**
1. Provide validation and empathy
2. Offer immediate connection to crisis resources
3. Queue for priority human callback within 5 minutes
4. Continue supportive conversation while awaiting handoff

#### Tier 3: ELEVATED (Enhanced Monitoring)
**Response Time:** Within same session

Keywords and Patterns:
- General distress: "estoy muy mal," "no se que hacer"
- Isolation indicators: "nadie me entiende," "estoy solo/a"
- Hopelessness: "nada va a cambiar," "no tiene caso"
- Recent loss: "perdi mi trabajo," "me dejo mi pareja"
- Financial desperation: "no tengo para comer," "me van a quitar la casa"

**Action Protocol:**
1. Increase empathy and validation in responses
2. Proactively offer human support option
3. Provide relevant resources
4. Schedule follow-up if appropriate

### 1.2 Sentiment Analysis Implementation

Based on research from [Nature Scientific Reports](https://www.nature.com/articles/s41598-025-17242-4) and [Frontiers in Psychiatry](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2025.1634714/full):

**Hybrid Approach Required:**
- Rule-based safety nets for detection and escalation
- LLM-driven relational support for conversation
- Never rely solely on AI for crisis detection

**Sentiment Signals to Monitor:**
- Urgency markers (exclamation, repetition)
- Temporal immediacy ("ahora," "ya")
- Finality language ("nunca," "siempre," "todo")
- Emotional intensity shifts within session
- Response latency patterns

### 1.3 False Positive Handling

Per [EA Forum research](https://forum.effectivealtruism.org/posts/CKykK8LWdqGsJuTK8/evaluating-llms-for-suicide-risk-detection-can-ai-catch-a-1):

**Critical Limitation:** AI systems often miss ambiguous expressions like "Me pregunto sobre la muerte ultimamente..."

**Best Practice:**
- Err on the side of caution (false positives are acceptable)
- Never argue or "correct" crisis detection
- Provide resources even if uncertain
- Allow graceful continuation if user indicates safety

```
Example Recovery Flow:
User: "No, no estoy pensando en hacerme dano, solo estoy muy triste."
AI: "Gracias por aclararmelo. Es completamente valido sentirse triste.
Estoy aqui para escucharte. Si en algun momento cambias de opinion
o necesitas apoyo adicional, estos recursos estan disponibles las 24 horas:
[recursos]. Ahora, cuentame mas sobre lo que estas sintiendo."
```

### 1.4 C-SSRS Integration

The [Columbia-Suicide Severity Rating Scale](https://www.columbiapsychiatry.org/research-labs/columbia-suicide-severity-rating-scale-c-ssrs) provides a validated framework:

**Screening Questions (Adapt for Conversational Context):**
1. Wish to be dead: "Has deseado estar muerto/a o poder dormirte y no despertar?"
2. Suicidal thoughts: "Has tenido pensamientos de acabar con tu vida?"
3. Suicidal thoughts with method: "Has pensado en como lo harias?"
4. Suicidal intent: "Has tenido la intencion de actuar en estos pensamientos?"
5. Active planning: "Has empezado a planear o preparar algo?"

**Implementation Note:** These should be deployed sensitively by human agents or in structured assessment flows, not as cold AI questions.

---

## 2. Trauma-Informed Conversation Design

### 2.1 Core Principles

Based on research from [Dartmouth/NEJM AI Trial](https://ai.nejm.org/doi/full/10.1056/AIoa2400802) and [Nature mental health research](https://www.nature.com/articles/s44184-024-00097-4):

**Five Pillars of Trauma-Informed AI:**
1. **Safety** - Physical and emotional safety in every interaction
2. **Trustworthiness** - Clear, consistent, transparent communication
3. **Choice** - User maintains control of conversation pace/direction
4. **Collaboration** - Partnership model, not authority model
5. **Empowerment** - Focus on strengths and capabilities

### 2.2 Language Patterns to USE

**Validation Phrases:**
- "Lo que sientes es completamente valido."
- "Muchas personas en situaciones similares se sienten asi."
- "Gracias por confiar en mi para compartir esto."
- "Escucho que esto ha sido muy dificil para ti."
- "Tu experiencia importa."

**Empowerment Language:**
- "Tu conoces mejor tu situacion."
- "Que te gustaria hacer ahora?"
- "Tienes opciones, y estoy aqui para explorarlas contigo."
- "Has demostrado mucha fortaleza al buscar ayuda."
- "Que apoyo te seria mas util en este momento?"

**Pacing and Control:**
- "Podemos ir al ritmo que necesites."
- "No tienes que compartir mas de lo que te sientas comodo/a."
- "Podemos hacer una pausa cuando quieras."
- "Si hay algo que no quieres discutir, esta bien."

### 2.3 Language Patterns to AVOID

Based on [Brown University research on AI ethics violations](https://www.brown.edu/news/2025-10-21/ai-mental-health-ethics):

**Never Use:**
- Platitudes: "Todo va a estar bien," "El tiempo lo cura todo"
- Minimizing: "Al menos no te paso X," "Otros lo tienen peor"
- Advice-giving before understanding: "Deberias hacer X"
- False empathy: "Te entiendo perfectamente" (AI cannot truly understand)
- Blame language: "Por que no lo dejaste antes?"
- Rushed problem-solving: Jumping to solutions before validation
- Condescension: "Calmate," "No exageres"

**Warning from Research:**
> "Chatbots were found to dominate conversations, reinforce false beliefs, create false intimacy through phrases like 'I understand' or 'I care about you,' and fail to refer users to appropriate resources." - Brown University Study

### 2.4 Re-traumatization Prevention

Per [Stanford HAI research](https://hai.stanford.edu/news/exploring-the-dangers-of-ai-in-mental-health-care):

**Key Protocols:**
1. **Never force disclosure** - Let users share at their own pace
2. **Avoid graphic details** - Don't ask for specifics of abuse/trauma
3. **No interrogative questioning** - Avoid "why" questions about trauma
4. **Recognize triggers** - Monitor for distress signals during conversation
5. **Offer breaks** - Proactively suggest pausing if intensity increases
6. **Ground before ending** - Ensure user is stable before closing session

**Safe Conversation Closure:**
```
"Antes de terminar, quiero asegurarme de que estes en un lugar seguro
emocionalmente. Como te sientes en este momento? Hay algo mas que
pueda hacer para apoyarte hoy?"
```

---

## 3. Discrete Interface Design (DV Services)

### 3.1 Quick Exit Mechanisms

Based on [Oomph Inc best practices](https://www.oomphinc.com/insights/user-safety-quick-exit-best-practices/) and [Design Patterns for Mental Health](https://designpatternsformentalhealth.org/examples/providing-a-quick-exit-button/):

**Button Design Requirements:**
- Visible on every page without scrolling
- Large enough for panicked clicks (minimum 44x44px for mobile)
- Clear but not attention-grabbing color (avoid red which may draw abuser attention)
- Position: Top right corner, consistent across all pages

**Button Labeling:**
Per user testing, avoid confusing labels:
- AVOID: "Quick Exit" (users don't understand)
- AVOID: "Escape" (potentially triggering for survivors)
- USE: "Salir" with neutral icon
- CONSIDER: Just an "X" icon with clear function

**Functionality Specifications:**
1. Single click exits to neutral site (weather.com, Google homepage)
2. Opens new window/tab to mask browsing
3. Keyboard shortcut: ESC key (with accessible notification)
4. On mobile: Shake gesture option

### 3.2 Fake Website Redirect System

**Redirect Targets (Mexico-appropriate):**
- clima.com.mx (weather)
- Google Mexico homepage
- Generic news site
- Recipe website

**Technical Implementation:**
```javascript
// Example redirect behavior
function quickExit() {
  window.open('https://www.google.com.mx', '_newtab');
  window.location.replace('https://clima.com.mx');
  // Replace location prevents back button return
}
```

### 3.3 History Deletion Guidance

Per [Tech Safety Net Project](https://www.techsafety.org/exit-from-this-website-quickly):

**Critical Limitation:** Quick exit buttons cannot delete browser history.

**Required User Education:**
- Provide clear instructions for deleting browser history
- Include device-specific guides (Android, iOS, desktop browsers)
- Explain incognito/private browsing mode
- Warn about device monitoring capabilities

**Sample Instructions to Include:**
```
IMPORTANTE: Este boton te ayuda a salir rapidamente, pero NO borra
tu historial de navegacion. Si tu pareja revisa tu telefono o computadora:

1. Usa modo incognito/privado antes de entrar
2. Borra tu historial despues de cada visita
3. Considera usar el dispositivo de una amiga, biblioteca, o trabajo
4. Llama al 800-108-4053 (Linea de la Mujer) desde telefono seguro
```

### 3.4 Code Word Implementation

Based on [Domestic Shelters research](https://www.domesticshelters.org/hope-chat-ai) and [YES! Magazine](https://www.yesmagazine.org/opinion/2023/05/12/domestic-violence-survivors-cheat-codes):

**Code Word System Design:**

**Purpose:** Allow survivors to request help covertly when abuser may be monitoring.

**Implementation for Mujeres IQM:**
1. Establish known code phrases through community outreach
2. Train AI to recognize and respond appropriately
3. Ensure immediate escalation without alarming responses

**Example Code Words:**
- "Estoy buscando una mascara para el frio" = Need immediate help
- "Quiero informacion sobre la receta de mi abuela" = Need shelter information
- "Tengo una cita con el dentista" = Can we schedule a callback at safe time?

**AI Response Protocol:**
```
User: "Hola, estoy buscando una mascara para el frio."

AI (appears normal but activates protocol):
"Claro, te puedo ayudar con eso. Para las mascaras mas calientes,
te recomiendo visitar [neutral information]."

[Backend: Alert human agent, prepare callback, log as priority]
[Human agent calls back with cover story if needed]
```

### 3.5 Anonymous Access Principles

Per [Sophia chatbot by Spring ACT](https://springact.org/sophia-chatbot/):

**Best Practice Features:**
- No account creation required for initial contact
- No personal data stored on device
- Evidence storage on secure external servers (Swiss standard)
- User controls all data access
- Automatic session data deletion option

---

## 4. Dignity-Preserving Design (Social Services)

### 4.1 Rights-Based Framing vs. Charity

Based on [Harvard Kennedy School research](https://www.hks.harvard.edu/faculty-research/policy-topics/social-policy/does-reducing-stigma-increase-participation-benefit) and [UNICEF disability rights framework](https://www.unicef.org/documents/rights-based-approach-disability-context-mental-health):

**Language Transformation:**

| Charity Model (AVOID) | Rights Model (USE) |
|----------------------|-------------------|
| "Ayuda para los necesitados" | "Programas a los que tienes derecho" |
| "Beneficios para pobres" | "Apoyos ciudadanos universales" |
| "Te damos una oportunidad" | "Ejerces tu derecho" |
| "Estamos aqui para ayudarte" | "Este programa existe para ti" |
| "Aplicar para beneficencia" | "Acceder a tus derechos" |

**Research Finding:**
> "Subtle changes to the framing of rental assistance increased interest in the program by 36% and completed applications by about 11%, with potentially larger effects for renters of color." - Harvard Kennedy School

### 4.2 Income Verification Language

**Stigma-Reducing Approaches:**

**AVOID:**
- "Prueba que eres pobre"
- "Documentos de ingresos minimos"
- "Certificado de pobreza"
- "Comprobante de necesidad"

**USE:**
- "Documentos de ingresos" (neutral)
- "Comprobante de situacion economica"
- "Informacion para determinar elegibilidad"
- "Requisitos administrativos del programa"

**Conversational Approach:**
```
AI: "Para completar tu acceso al programa, necesito pedirte algunos
documentos administrativos. Esto es parte del proceso estandar para
todos los ciudadanos. Que documentos tienes disponibles de los siguientes?"
```

### 4.3 Eligibility Denial Handling

**Key Principles:**
1. Never leave user without alternatives
2. Explain criteria transparently
3. Offer pathway to appeal or alternative programs
4. Maintain dignity throughout

**Sample Denial Response:**
```
AI: "Basado en la informacion que proporcionaste, este programa especifico
tiene criterios de elegibilidad que no coinciden con tu situacion actual.
Esto NO significa que no mereces apoyo - hay otros programas que pueden
ser adecuados para ti.

Te gustaria que revisemos juntos otras opciones disponibles?
Tambien puedes solicitar una revision de tu caso si consideras
que hubo un error en la evaluacion."
```

### 4.4 Multi-Barrier Accessibility

Per [Digital Poverty Alliance](https://www.edtechinnovationhub.com/comment/breaking-barriers-the-role-of-digital-accessibility-in-reducing-digital-poverty) and [EU AI Act accessibility requirements](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2024/12/inclusive-ai-for-people-with-disabilities--key-considerations.html):

**Accessibility Requirements:**
1. **Digital Literacy** - Simple, plain language (6th-grade reading level)
2. **Language Access** - Indigenous language support (Otomi, Nahuatl for Queretaro)
3. **Device Access** - Mobile-first design, low-bandwidth optimization
4. **Visual Impairment** - Screen reader compatibility, high contrast options
5. **Hearing Impairment** - Text-based alternatives to all audio
6. **Cognitive Accessibility** - Step-by-step guidance, progress indicators
7. **Time Constraints** - Ability to save progress, resume later

---

## 5. Human Handoff Protocols

### 5.1 Warm Transfer Specifications

Based on [Topflight Apps mental health chatbot guide](https://topflightapps.com/ideas/build-mental-health-chatbot/) and [Social Intents handoff guide](https://www.socialintents.com/blog/ai-chatbot-with-human-handoff/):

**Warm Transfer Protocol:**
1. **Announce handoff** - "Te voy a conectar con un especialista humano que puede ayudarte mejor."
2. **Prepare user** - "Por favor espera un momento mientras te conecto."
3. **Transfer context** - Full conversation summary to human agent
4. **Confirm connection** - Human acknowledges and references conversation
5. **Graceful AI exit** - AI confirms handoff and availability for future

**Sample Handoff Script:**
```
AI: "Lo que me estas compartiendo es importante y creo que una
persona especializada te puede apoyar mejor. Te voy a conectar
con [nombre/rol] quien ya tiene el contexto de nuestra conversacion.

Estaras en buenas manos. Estoy aqui 24/7 si necesitas algo mas despues."

[Transfer to human with full context summary]

Human Agent: "Hola [nombre], soy [nombre], [rol]. [Nombre AI]
me comparti lo que estaban hablando. Entiendo que estas pasando
por [resumen]. Estoy aqui para ayudarte..."
```

### 5.2 Context Preservation

**Data to Transfer:**
1. Full conversation transcript
2. Detected crisis level and keywords triggered
3. User-provided context (name, location if shared)
4. Services already discussed
5. User's stated needs/preferences
6. Emotional state indicators
7. Time in conversation

**Technical Requirement:**
- Real-time context transfer (no user repetition needed)
- Secure, encrypted transmission
- Audit trail for compliance

### 5.3 SLA Requirements

Based on crisis intervention standards and [Therabot safety protocols](https://talk.crisisnow.com/the-generative-ai-therapy-chatbot-will-see-you-now/):

| Crisis Tier | Initial Response | Human Contact | Resolution |
|------------|------------------|---------------|------------|
| IMMEDIATE (Tier 1) | < 30 seconds | < 2 minutes | Active monitoring |
| URGENT (Tier 2) | < 1 minute | < 5 minutes | Within 1 hour |
| ELEVATED (Tier 3) | < 2 minutes | < 15 minutes | Same day |
| Standard | < 30 seconds | On request | Per policy |

### 5.4 After-Hours Handling

**24/7 Coverage Requirements:**

**Option 1: Full Human Coverage**
- Staff trained crisis responders around the clock
- Expensive but gold standard for mental health/DV

**Option 2: Tiered After-Hours**
- Tier 1/2: 24/7 human coverage
- Tier 3/Standard: AI with next-day callback queue
- Clear communication of wait times

**Option 3: Partner Integration**
- Route after-hours crisis to Linea de la Vida (800-290-0024)
- Route DV to Linea de la Mujer (800-108-4053)
- AI provides warm introduction

**After-Hours AI Script:**
```
AI: "Entiendo que esto es urgente. En este momento nuestro equipo
no esta disponible, pero te puedo conectar directamente con la
Linea de la Vida, donde hay profesionales las 24 horas.

El numero es 800-290-0024 (gratuito).

Si prefieres, puedo agendar una llamada de nuestro equipo
para manana a primera hora. Que prefieres?"
```

---

## 6. Legal Compliance (Mexico)

### 6.1 Mandatory Reporting Requirements

Based on [NOM-046-SSA2-2005](https://www.gob.mx/conapo/documentos/norma-oficial-mexicana-046-ssa2-2005-violencia-familiar-sexual-y-contra-las-mujeres-criterios-para-la-prevencion-y-atencion) and [Ley General de Victimas](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGV.pdf):

**NOM-046-SSA2-2005: Violence Against Women**
- **Applicability:** All healthcare institutions (public, private, social)
- **Requirement:** Detection, medical/psychological attention, and notification of domestic violence cases
- **Notification:** Cases must be reported to competent authorities (Ministerio Publico)
- **Obligation:** Inform victims of their right to report to authorities

**When AI Must Escalate to Human for Reporting:**
1. Any disclosure of abuse (current or recent)
2. Child abuse or neglect indicators
3. Elder abuse
4. Sexual violence
5. Imminent danger to self or others

**AI Disclosure Statement:**
```
AI: "Antes de continuar, quiero que sepas que soy un asistente virtual
del Gobierno de Queretaro. Nuestra conversacion es confidencial, pero
hay algunas situaciones donde la ley requiere que un profesional
intervenga - por ejemplo, si hay riesgo de dano a ti o a alguien mas.

Si eso ocurre, te lo comunicare antes de tomar cualquier accion.
Esta bien si continuamos?"
```

### 6.2 Data Retention for Sensitive Conversations

**Privacy Framework:**
- [Ley Federal de Proteccion de Datos Personales](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf)
- INAI Data Protection Guidelines for Violence Victims

**Key Requirements:**
1. **Consent:** Clear, informed consent before data collection
2. **Minimization:** Collect only necessary data
3. **Purpose Limitation:** Data used only for stated purposes
4. **Security:** Encryption, access controls, audit trails
5. **Access Control:** Limited to authorized personnel
6. **Retention Limits:** Define maximum retention periods
7. **Right to Delete:** User can request deletion (with exceptions for legal holds)

**Special Considerations for Violence Victims:**
Per [INAI Guide for Violence Victims](https://home.inai.org.mx/wp-content/documentos/GuiasTitulares/Gu%C3%ADa_PDP_Violencia_m.pdf):
- Privacy notice must be communicated before treatment
- Data access limited to those requiring it for victim assistance
- Enhanced security measures for sensitive data
- Respect for victim autonomy in all data decisions

### 6.3 AI-Specific Regulations (Emerging)

Per [Mexico AI Legislation 2025](https://www.globalpolicywatch.com/2025/03/new-artificial-intelligence-legislation-in-mexico/):

**Status:** Federal Law Regulating Artificial Intelligence under Senate discussion (expected 2026)

**Key Provisions (Proposed):**
- Risk-based compliance framework
- National Commission for AI (CONAIA) oversight
- Authorization requirements for high-risk AI systems
- Transparency and accountability mandates

**Recommendation:** Design systems to exceed current requirements in anticipation of stricter regulation.

### 6.4 Ley General de Victimas Compliance

**Victim Rights AI Must Respect:**
1. Protection of physical/psychological wellbeing
2. Privacy and dignity protection
3. Right to report to authorities (must inform)
4. Access to victim's assistance services
5. Non-discrimination in service delivery
6. Cultural and gender-sensitive attention

---

## 7. Specific Recommendations by Domain

### 7.1 Psicologia SEJUVE (Youth Mental Health)

**Context:** Young people seeking mental health support, suicide prevention, psychological crisis

**Priority Protocols:**
1. **C-SSRS Integration** - Implement tiered suicide risk assessment
2. **Youth-Specific Language** - Adapt vocabulary for adolescents
3. **Confidentiality Balance** - Explain limits with minors
4. **School Integration** - Coordinate with USEBEQ counselors
5. **After-Hours Priority** - 24/7 crisis coverage essential

**Special Considerations:**
- Higher false-positive acceptance for youth
- Parent/guardian notification protocols for minors
- Gaming/social media awareness in language
- Peer pressure and bullying recognition

**Sample Opening:**
```
AI: "Hola! Soy el asistente de Psicologia SEJUVE. Estoy aqui para
escucharte y conectarte con apoyo si lo necesitas. Todo lo que
compartas es confidencial, a menos que haya un riesgo serio -
y si eso pasa, te lo dire primero.

Como te sientes hoy?"
```

### 7.2 Mujeres IQM (Domestic Violence/Women's Services)

**Context:** Survivors of domestic violence, sexual violence, gender-based discrimination

**Priority Protocols:**
1. **Quick Exit Implementation** - Mandatory on all interfaces
2. **Code Word System** - Trained recognition and response
3. **Evidence Preservation** - Secure documentation capability
4. **Shelter Access** - Confidential location information
5. **Legal Support Pathway** - Connection to attorneys

**Special Considerations:**
- Device safety warnings upfront
- Coercive control recognition
- Economic abuse indicators
- Child custody implications
- Immigration status sensitivity

**Sample Opening:**
```
AI: "Bienvenida al IQM. Este es un espacio seguro y confidencial.

IMPORTANTE: Si alguien esta cerca y necesitas salir rapidamente,
presiona el boton [Salir] o la tecla ESC. Te llevara a otra pagina.

Como puedo apoyarte hoy?"
```

**Code Word Training Examples:**
| Code Phrase | Meaning | AI Response |
|------------|---------|-------------|
| "Receta de mi abuela" | Need shelter info | Provide neutral response, escalate internally |
| "Mascara para el frio" | In immediate danger | Appear normal, silent alert to staff |
| "Cita con el dentista" | Safe callback time | Schedule at user-specified safe time |

### 7.3 Conciliacion Laboral (Labor/Employment Crisis)

**Context:** Job loss, wage theft, workplace abuse, financial crisis

**Priority Protocols:**
1. **Financial Crisis Detection** - Food/housing insecurity triggers
2. **Dignity Language** - Rights-based framing for workers
3. **Multi-Barrier Access** - Low literacy accommodation
4. **Integration with SEDESOQ** - Warm referrals for social programs
5. **Legal Rights Education** - Clear explanation of worker protections

**Special Considerations:**
- Shame around job loss
- Family financial responsibility stress
- Documentation for undocumented workers
- Employer retaliation concerns
- Depression/anxiety secondary to job loss

**Sample Response to Job Loss:**
```
User: "Me corrieron de mi trabajo ayer sin explicacion."

AI: "Lamento escuchar eso. Perder un trabajo puede ser muy dificil,
y es natural sentirse preocupado. Quiero que sepas que tienes derechos
como trabajador, y hay opciones disponibles para ti.

Primero, como te sientes en este momento? Estoy aqui para escucharte.

Cuando estes listo, puedo explicarte tus derechos laborales y los
pasos que puedes tomar. Tambien puedo conectarte con programas de
apoyo si lo necesitas."
```

### 7.4 SEDESOQ (Social Development Programs)

**Context:** Poverty assistance, social programs, food security, housing support

**Priority Protocols:**
1. **Universal Rights Framing** - Never charity language
2. **Plain Language** - 6th-grade reading level
3. **Multi-Channel Access** - Voice, text, in-person pathways
4. **Eligibility Transparency** - Clear criteria explanation
5. **Barrier Reduction** - Minimal documentation requirements

**Special Considerations:**
- Generational poverty stigma
- Indigenous language access (Otomi, Nahuatl)
- Digital literacy barriers
- Transportation to offices
- Document access challenges

**Sample Eligibility Conversation:**
```
User: "Quiero saber si califico para algun programa."

AI: "Claro, vamos a revisar juntos las opciones disponibles para ti.
Estos son programas a los que todos los ciudadanos de Queretaro
tienen derecho si cumplen ciertos requisitos.

Para ayudarte mejor, me puedes decir:
1. Cuantas personas viven en tu hogar?
2. Tienes hijos en edad escolar?
3. Trabajas actualmente o estas buscando empleo?

Con esta informacion puedo identificar los programas que aplican
para tu situacion."
```

**Denial Handling:**
```
AI: "Basado en lo que me compartiste, el programa [X] tiene requisitos
que no coinciden con tu situacion actual. Esto es solo por los
criterios administrativos del programa, no por ti.

La buena noticia es que hay otros tres programas que si podrian
aplicar: [lista]. Te gustaria que los revisemos juntos?"
```

---

## 8. Implementation Checklist

### 8.1 Technical Requirements

- [ ] Tiered keyword detection system
- [ ] Sentiment analysis integration
- [ ] Quick exit functionality (all interfaces)
- [ ] Session data encryption
- [ ] Secure evidence storage
- [ ] Context transfer for handoffs
- [ ] Audit logging for compliance
- [ ] Mobile-first responsive design
- [ ] Accessibility compliance (WCAG 2.1 AA)
- [ ] Multi-language support

### 8.2 Human Resources Requirements

- [ ] 24/7 crisis response staff (Tier 1/2)
- [ ] Trained counselors for mental health
- [ ] DV-specialized advocates
- [ ] Legal support access
- [ ] Indigenous language interpreters
- [ ] Regular staff training on protocols

### 8.3 Partnership Requirements

- [ ] Linea de la Vida integration (800-290-0024)
- [ ] Linea de la Mujer integration (800-108-4053)
- [ ] Emergency services coordination (911)
- [ ] Shelter network access
- [ ] Legal aid organizations
- [ ] Healthcare provider network

### 8.4 Compliance Documentation

- [ ] Privacy notices (per domain)
- [ ] Consent mechanisms
- [ ] Data retention policies
- [ ] Mandatory reporting protocols
- [ ] Audit trail procedures
- [ ] Staff training records
- [ ] Incident response plans

---

## Sources

### Crisis Detection and Suicide Prevention
- [PMC: Generative AI Response to Suicide Inquiries](https://pmc.ncbi.nlm.nih.gov/articles/PMC12371289/)
- [Nature Scientific Reports: Mental Health Chatbot Performance](https://www.nature.com/articles/s41598-025-17242-4)
- [Frontiers in Psychiatry: LLM-based Suicide Intervention Chatbot](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2025.1634714/full)
- [EA Forum: LLMs for Suicide Risk Detection](https://forum.effectivealtruism.org/posts/CKykK8LWdqGsJuTK8/evaluating-llms-for-suicide-risk-detection-can-ai-catch-a-1)
- [Columbia-Suicide Severity Rating Scale](https://www.columbiapsychiatry.org/research-labs/columbia-suicide-severity-rating-scale-c-ssrs)
- [HHS 2024 National Strategy for Suicide Prevention](https://www.hhs.gov/programs/prevention-and-wellness/mental-health-substance-use-disorder/national-strategy-suicide-prevention/index.html)

### Trauma-Informed Design
- [NEJM AI: Randomized Trial of Generative AI Therapy Chatbot](https://ai.nejm.org/doi/full/10.1056/AIoa2400802)
- [Nature: User Experiences with AI Chatbots for Mental Health](https://www.nature.com/articles/s44184-024-00097-4)
- [Brown University: AI Chatbots Violate Mental Health Ethics](https://www.brown.edu/news/2025-10-21/ai-mental-health-ethics)
- [Stanford HAI: Dangers of AI in Mental Health Care](https://hai.stanford.edu/news/exploring-the-dangers-of-ai-in-mental-health-care)
- [SAGE Journals: Mental Health Chatbot Conversation Design](https://journals.sagepub.com/doi/abs/10.1177/09526951241305274)

### Domestic Violence and Safety
- [Oomph Inc: Quick Exit Button Best Practices](https://www.oomphinc.com/insights/user-safety-quick-exit-best-practices/)
- [Design Patterns for Mental Health: Quick Exit](https://designpatternsformentalhealth.org/examples/providing-a-quick-exit-button/)
- [Spring ACT: Sophia Chatbot](https://springact.org/sophia-chatbot/)
- [Domestic Shelters: Hope Chat AI](https://www.domesticshelters.org/hope-chat-ai)
- [NNEDV: AI Privacy and Safety for Abuse Survivors](https://nnedv.org/latest_update/new-openai-court-order-raises-serious-concerns-about-ai-privacy-and-safety-for-survivors-of-abuse/)
- [Frontiers: AI Chatbots for Gender-Based Violence](https://www.frontiersin.org/journals/political-science/articles/10.3389/fpos.2025.1631881/full)
- [Tech Safety Net: Exit From Website Quickly](https://www.techsafety.org/exit-from-this-website-quickly)
- [YES! Magazine: Code Words for DV Survivors](https://www.yesmagazine.org/opinion/2023/05/12/domestic-violence-survivors-cheat-codes)

### Dignity-Preserving Social Services
- [Harvard Kennedy School: Reducing Stigma in Benefit Programs](https://www.hks.harvard.edu/faculty-research/policy-topics/social-policy/does-reducing-stigma-increase-participation-benefit)
- [UNICEF: Rights-Based Approach to Disability and Mental Health](https://www.unicef.org/documents/rights-based-approach-disability-context-mental-health)
- [Saint Michael's College: Human Dignity in AI](https://www.smcvt.edu/about-smc/news/2025/november/beyond-data-points-preserving-human-dignity-in-the-age-of-ai/)
- [Clifford Chance: Inclusive AI for People with Disabilities](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2024/12/inclusive-ai-for-people-with-disabilities--key-considerations.html)
- [Digital Poverty Alliance: Digital Accessibility](https://www.edtechinnovationhub.com/comment/breaking-barriers-the-role-of-digital-accessibility-in-reducing-digital-poverty)

### Human Handoff Protocols
- [Topflight Apps: Building Mental Health Chatbots](https://topflightapps.com/ideas/build-mental-health-chatbot/)
- [Social Intents: AI Chatbot with Human Handoff](https://www.socialintents.com/blog/ai-chatbot-with-human-handoff/)
- [Crisis Talk: Therabot Safety Protocols](https://talk.crisisnow.com/the-generative-ai-therapy-chatbot-will-see-you-now/)
- [SpurNow: Chatbot to Human Handoff Guide](https://www.spurnow.com/en/blogs/chatbot-to-human-handoff)

### Mexico Legal Framework
- [NOM-046-SSA2-2005: Violence Against Women](https://www.gob.mx/conapo/documentos/norma-oficial-mexicana-046-ssa2-2005-violencia-familiar-sexual-y-contra-las-mujeres-criterios-para-la-prevencion-y-atencion)
- [Ley General de Victimas](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGV.pdf)
- [INAI: Data Protection Guide for Violence Victims](https://home.inai.org.mx/wp-content/documentos/GuiasTitulares/Gu%C3%ADa_PDP_Violencia_m.pdf)
- [Mexico AI Legislation 2025](https://www.globalpolicywatch.com/2025/03/new-artificial-intelligence-legislation-in-mexico/)
- [ICLG: Mexico Digital Health Laws 2025](https://iclg.com/practice-areas/digital-health-laws-and-regulations/mexico)
- [Chambers: Mexico AI Practice Guide 2025](https://practiceguides.chambers.com/practice-guides/artificial-intelligence-2025/mexico)

---

*Document Version: 1.0*
*Last Updated: February 2026*
*Research conducted for Gobierno de Queretaro AI Platform*
