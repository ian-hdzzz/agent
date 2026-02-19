# Voice AI Design Guidelines for Government Services

> **Research Document for MARIA - Gobierno de Queretaro AI Platform**
>
> Last Updated: February 2026
>
> Voice channels are critical for accessibility, serving elderly users (60%+ for transport services), low-literacy populations, and replacing legacy IVR systems across all 13 government domains.

---

## Executive Summary

Voice AI represents a transformative opportunity for government services, enabling natural language interactions that dramatically improve accessibility and citizen experience. The global voice AI market is projected to grow from $3.14 billion in 2024 to $47.5 billion by 2034 (34.8% CAGR), while 37.6% of companies plan to fully replace IVRs with AI triage agents by 2026.

This document provides comprehensive guidelines for implementing voice AI in the Gobierno de Queretaro context, covering conversation design, Spanish language considerations, emotional intelligence, accessibility, error handling, privacy, and domain-specific requirements.

---

## 1. Voice Conversation Design Principles

### 1.1 Turn Length Optimization

**Research Finding**: Conversational design should focus on helping users complete tasks smoothly rather than imitating human conversation perfectly. Users "don't expect an assistant to be witty or fully human-like, but they do expect it to understand their intent and respond appropriately."

**Guidelines**:
- **Keep responses concise**: 2-3 sentences maximum for informational responses
- **Front-load critical information**: Most important details first
- **Use progressive disclosure**: Offer more details only when requested
- **Avoid monologues**: Break long responses into interactive turns

**Example Pattern**:
```
POOR: "Su tramite de verificacion vehicular puede realizarse en cualquiera de
los 47 centros autorizados distribuidos en todo el estado. Los horarios de
atencion son de lunes a viernes de 8:00 a 18:00 horas y sabados de 8:00 a
14:00 horas. Necesitara traer su tarjeta de circulacion, identificacion
oficial y el pago correspondiente..."

BETTER: "Puedo ayudarle a encontrar un centro de verificacion cercano.
Cual es su codigo postal?"
```

### 1.2 Confirmation Patterns

**Research Finding**: Organizations implementing orchestrated voice AI report 67% higher customer satisfaction scores with 89% higher first-contact resolution when using proper confirmation patterns.

**Three-Level Confirmation Framework**:

| Level | Use Case | Pattern |
|-------|----------|---------|
| **Implicit** | Low-risk, reversible | Echo back subtly in response |
| **Explicit** | Medium-risk, identifiers | "Entendi [X], es correcto?" |
| **Transactional** | High-risk, irreversible | "Para confirmar [accion], diga 'Confirmo'" |

**Domain-Specific Confirmations**:
- **Vehicles**: Plate numbers spelled back letter-by-letter
- **Payments**: Amount and concept repeated with pause for correction
- **Appointments**: Date, time, and location confirmed with SMS backup
- **Personal Data**: Last 4 digits only for privacy

### 1.3 Disambiguation Strategies

**Research Finding**: "Users often provide incomplete or ambiguous instructions. Effective NLU identifies uncertainty and prompts clarification without breaking conversational interface design."

**Strategies**:

1. **Constrained Choices** (preferred for voice):
   ```
   "Quiere consultar sobre verificacion vehicular o renovacion de licencia?"
   ```

2. **Contextual Clarification**:
   ```
   "Cuando dice 'mi pago', se refiere al pago de predial o al de agua?"
   ```

3. **Confidence-Based Routing**:
   - High confidence (>85%): Proceed with implicit confirmation
   - Medium confidence (60-85%): Explicit confirmation before action
   - Low confidence (<60%): Ask for clarification

### 1.4 Barge-In Handling

**Research Finding**: "Modern implementations achieve end-to-end latencies of less than 100 milliseconds from speech detection to system response." Post-implementation of sophisticated barge-in detection, accuracy improved to 95%, and interruption handling time decreased by 40%.

**Implementation Guidelines**:

1. **Enable Full Duplex Processing**: Allow simultaneous listening and speaking
2. **Target <200ms Response**: Stop speaking within 200ms when interrupted
3. **Implement Voice Activity Detection (VAD)**: Distinguish speech from noise
4. **Handle Communicative Markers**: "uh-huh", "si", "ok" should not trigger full interrupts
5. **Echo Cancellation**: Prevent self-speech from triggering interrupts

**Barge-In Scenarios**:

| Scenario | Response |
|----------|----------|
| User interrupts with correction | Stop immediately, acknowledge correction |
| User interrupts with "si" | Continue without pause |
| User interrupts with question | Complete current sentence, then address |
| Background noise detected | Lower volume, continue |

---

## 2. Spanish Language Considerations

### 2.1 Regional Accent Handling (Mexican Spanish)

**Research Finding**: ElevenLabs and other providers offer Mexican Spanish-specific voice generation that "captures the unique aspects of the Mexican language, including its regional dialects." Most ASR models are trained on standard American or British English, leading to frequent misrecognition in multicultural markets.

**Mexican Spanish Specificities**:

| Feature | Standard Spanish | Mexican Spanish | Implementation |
|---------|------------------|-----------------|----------------|
| Diminutives | pequeno | chiquito, -ito suffix | Train on local corpus |
| Slang integration | momento | momentito, ratito | Include in vocabulary |
| Consonant sounds | /s/ vs /z/ distinction | Seseo (merged) | Configure ASR |
| Vocabulary | autobus | camion | Add regional synonyms |
| Speed | ~150 wpm | ~170 wpm | Adjust VAD timing |

**ASR Training Recommendations**:
- Source transcripts from Queretaro-specific interactions
- Include code-switching patterns (Spanish/English)
- Train on informal speech patterns ("lemme" equivalents like "orale", "andale")
- Accent adaptation can dramatically reduce WER in real calls

### 2.2 Formal vs. Informal Register

**Guidelines for Government Services**:

| Context | Register | Pronoun | Example |
|---------|----------|---------|---------|
| Default | Formal | Usted | "Como puedo ayudarle?" |
| Youth services (<25) | Semi-formal | Usted (softer) | "Que necesitas?" acceptable |
| Emergency/Crisis | Formal + empathetic | Usted | "Estoy aqui para ayudarle" |
| Repeat interactions | Slightly warmer | Usted | "Bienvenido de nuevo" |

**Never Use**:
- Overly casual slang in official transactions
- Tu form unless explicitly enabled for youth programs
- Diminutives for serious matters (legal, financial)

### 2.3 Technical Term Pronunciation

**Common Government Terms**:

| Term | Pronunciation Guide | Context |
|------|---------------------|---------|
| CURP | "Curp" (single syllable) | All domains |
| RFC | "Erre-Efe-Ce" | Tax matters |
| INE | "Ee-Ene-Ee" | Identification |
| IMSS | "I-M-S-S" | Health services |
| Predial | "Pre-DIAL" | Property tax |

**Number Verbalization**:
- Phone numbers: Groups of 2-3 digits with pauses
- Money: Full peso amounts, then centavos
- Dates: "Quince de septiembre de dos mil veinticinco"
- IDs: Character-by-character with NATO phonetic for letters

### 2.4 Date and Time Verbalization

**Date Formats**:
```
Written: 15/09/2025
Spoken: "Quince de septiembre de dos mil veinticinco"

Time formats:
Written: 14:30
Spoken: "Dos y media de la tarde" (casual)
         "Catorce treinta horas" (formal/appointments)
```

---

## 3. Emotional Intelligence in Voice

### 3.1 Tone Detection Approaches

**Research Finding**: "Modern systems can identify basic emotions with an accuracy of 70-90% under controlled conditions." Voice AI systems analyze over 100 voice parameters including amplitude, frequency, pitch variations, speech rate, and pauses.

**Detectable Emotional Indicators**:

| Emotion | Voice Markers | System Response |
|---------|---------------|-----------------|
| Frustration | Increased pitch, faster rate, louder | Acknowledge, simplify, offer human |
| Confusion | Hesitation, rising intonation, "um" | Clarify, slow down, offer alternatives |
| Urgency | Rapid speech, shortened phrases | Prioritize, skip pleasantries |
| Sadness | Lower pitch, slower rate, trailing off | Warmth, patience, crisis check |
| Anger | Volume spikes, sharp tone | De-escalate, validate, escalate |

**Implementation with ElevenLabs**:
- Use voice analysis APIs for real-time sentiment
- Configure response tone to match appropriate empathy level
- Trigger human escalation at sustained negative sentiment (>30 seconds)

### 3.2 Stress and Frustration Indicators

**Early Warning Signs**:
1. Repeated same request with increasing volume
2. Explicit frustration markers: "Ya le dije", "No me entiende"
3. Sighing or audible exhales
4. Interrupting before system completes responses
5. Request to speak with human

**Graduated Response Protocol**:

```
Level 1 (Mild stress detected):
- Slow speech rate by 10%
- Use warmer tone
- Simplify options to binary choices

Level 2 (Moderate frustration):
- Explicitly acknowledge: "Entiendo que esto puede ser frustrante"
- Offer immediate human escalation option
- Summarize progress made

Level 3 (High frustration/anger):
- Immediate human handoff offer
- Transfer with full context
- Flag interaction for quality review
```

### 3.3 Empathetic Response Patterns

**Framework for Empathetic Responses**:

1. **Acknowledge** the emotion: "Entiendo que esta situacion es dificil"
2. **Validate** the experience: "Tiene toda la razon en sentirse asi"
3. **Assist** with next steps: "Vamos a resolverlo juntos"

**Domain-Specific Empathy**:

| Domain | Scenario | Empathetic Response |
|--------|----------|---------------------|
| Psychology | Distress call | "Estoy aqui para escucharle. Tome su tiempo." |
| Women's Services | Safety concern | "Su seguridad es lo mas importante. Puedo conectarle con ayuda inmediata." |
| Social Services | Financial hardship | "Entiendo lo dificil que puede ser esta situacion. Hay programas que pueden ayudar." |
| Civil Registry | Loss notification | "Lamento mucho su perdida. Le acompano en este proceso." |

### 3.4 Crisis Detection via Voice

**Research Finding**: "Voice-based AI can assess suicide risk with accuracies superior to traditional survey-based approaches." Models can identify fearful/concerned emotions 82% of the time, sadness 77%, and anger 72%.

**Crisis Indicators for Immediate Escalation**:

| Indicator | Voice Marker | Protocol |
|-----------|--------------|----------|
| Suicidal ideation | Keywords + flat affect | Immediate human + crisis line |
| Domestic violence | Whispered, fearful, coded language | Safety protocol + resources |
| Medical emergency | Panic, breathlessness, pain indicators | 911 connection offered |
| Child in danger | Distress markers, specific keywords | Child protection protocol |

**Crisis Response Protocol**:
```
1. Detect: AI identifies crisis markers
2. Pause: Do not continue normal flow
3. Acknowledge: "Estoy escuchando algo importante"
4. Verify: "Esta usted en peligro en este momento?"
5. Connect: Human specialist or emergency services
6. Document: Flag for follow-up with consent
```

**Sensitive Services Integration**:
- Psychology domain: Built-in crisis detection at all times
- Women's Services: Domestic violence indicators
- Social Services: Financial desperation markers
- All domains: General suicide/self-harm detection

---

## 4. Accessibility Requirements

### 4.1 Speech Rate Guidelines

**Research Finding**: "VUI design should prioritize accessibility. Create voice interfaces that cater to a broad range of users, including those with disabilities."

**Speech Rate Standards**:

| User Group | Recommended Rate | Implementation |
|------------|------------------|----------------|
| General adult | 150-170 wpm | Default setting |
| Elderly (65+) | 120-140 wpm | Automatic for senior-flagged accounts |
| Cognitive accessibility | 100-120 wpm | User-configurable |
| Vision impaired | 150-180 wpm | Often prefer faster (experienced) |

**User Control Commands**:
- "Mas lento" / "Mas despacio" - Reduce rate 20%
- "Mas rapido" - Increase rate 20%
- "Repite" - Repeat at same rate
- "Repite mas lento" - Repeat at reduced rate

### 4.2 Repetition Handling

**Best Practices**:
1. **First repetition**: Exact repeat
2. **Second repetition**: Simplified language, slower
3. **Third repetition**: Offer alternative channel (SMS, human)

**Repetition Triggers**:
- Explicit: "Repita por favor", "Que dijo?", "No escuche"
- Implicit: Silence >5 seconds after information delivery
- Automatic: After complex information (dates, numbers, addresses)

### 4.3 Alternative Input Methods

**Multi-Modal Fallbacks**:

| Scenario | Alternative |
|----------|-------------|
| ASR repeatedly fails | "Puede escribir su respuesta por mensaje" |
| Sensitive information | "Le envio un enlace seguro para capturar sus datos" |
| Complex selection | "Le envio las opciones por mensaje para que elija" |
| Accent not recognized | "Puede deletrear su nombre?" |

**DTMF Fallback** (for phone-based systems):
- Always offer: "Tambien puede presionar 1 para X, 2 para Y"
- Critical for users with speech impairments
- Required for TTY/TDD compatibility

### 4.4 Screen Reader Compatibility

**For Voice + Visual Interfaces**:
- All visual elements must have voice equivalents
- Focus order must match logical voice flow
- Status updates announced audibly
- Error messages readable by screen readers

**WCAG 2.2 Compliance**:
- Level AA minimum for government services
- Voice alternatives for all visual content
- Keyboard navigation parallels voice commands
- Testing with JAWS, NVDA, VoiceOver required

### 4.5 Elderly User Considerations

**Research Finding**: "For seniors who struggle with movement, reaching for a phone, or manipulating small controls, voice commands are revolutionary." Government partnerships with AI companions like ElliQ show high adoption even among 80-90 year olds.

**Design Principles for Seniors**:

1. **Patience**: Longer response windows (8-10 seconds vs standard 5)
2. **Repetition**: Offer to repeat without judgment
3. **Simplicity**: Binary choices over multiple options
4. **Confirmation**: More explicit confirmations for all actions
5. **Human Option**: Always prominently available
6. **Familiar Patterns**: Mirror traditional phone tree expectations initially

---

## 5. Error Handling in Voice

### 5.1 Misrecognition Recovery

**Research Finding**: "Recovery quality is measured by whether the agent detects uncertainty, asks for clarification correctly, and completes the task without looping." The most telling KPIs are ASR accuracy under noise, recovery success after misrecognition, and task completion without repetition.

**Recovery Framework**:

```
Attempt 1: "No estoy seguro de haber entendido. Dijo [best guess]?"
Attempt 2: "Disculpe, podria repetir solo [specific element needed]?"
Attempt 3: "Parece que tenemos dificultad. Prefiere que le conecte con un agente?"
```

**Common Misrecognition Causes & Mitigations**:

| Cause | Mitigation |
|-------|------------|
| Background noise | "Parece que hay ruido de fondo. Puede moverse a un lugar mas tranquilo?" |
| Accent variation | Train on regional corpus, offer spelling option |
| Technical jargon | Provide synonyms: "Su CURP, tambien conocido como clave unica" |
| Code-switching | Include bilingual patterns in training |
| Informal speech | Map colloquialisms to formal intents |

### 5.2 "I Didn't Understand" Patterns

**Progressive Degradation**:

| Attempt | Response Pattern |
|---------|------------------|
| 1 | "Disculpe, no entendi bien. Puede repetir?" |
| 2 | "Sigo teniendo dificultad. Diga solo [key word needed]" |
| 3 | "Le ofrezco algunas opciones: Diga 1 para X, 2 para Y, o 3 para hablar con alguien" |
| 4 | Automatic human escalation with context |

**Avoid**:
- Repeating identical "no entendi" messages
- Blame language ("usted dijo algo incorrecto")
- Infinite loops without human escape
- Generic responses without guidance

### 5.3 Graceful Degradation

**Degradation Hierarchy**:

```
Full Voice AI -> Simplified Voice -> DTMF Menu -> Human Agent -> Callback
```

**Triggers for Degradation**:
- 3+ consecutive misrecognitions
- User explicit request
- Detected frustration
- Complex multi-part query
- System confidence below threshold

**Maintaining Context**:
- Transfer all conversation history to next level
- Summarize interaction for human agents
- Enable continuation from degraded state

### 5.4 Human Escalation Triggers

**Research Finding**: "The platform should make it easy to transfer calls to human agents when confidence drops, emotions escalate, or complexity increases. Handoffs should preserve context so customers do not need to repeat themselves."

**Automatic Escalation Triggers**:

| Trigger Category | Specific Triggers |
|------------------|-------------------|
| **Explicit Request** | "Agente", "Hablar con persona", "Humano" |
| **Repeated Failure** | 3+ failed recognition attempts |
| **Emotional Escalation** | Sustained frustration >30 seconds |
| **Complexity** | Multi-domain query, exceptions to standard process |
| **Risk** | Financial transactions >threshold, legal matters |
| **Crisis** | Safety concerns, emergency indicators |
| **VIP Routing** | Flagged accounts, specific case types |

**Handoff Protocol**:
```
1. Acknowledge: "Entiendo que prefiere hablar con alguien"
2. Summarize: "Le comunico con un agente y le paso el resumen de lo que hemos hablado"
3. Transfer: Include conversation transcript, detected intent, sentiment score
4. Warm Handoff: Agent greeted with context, not cold transfer
5. Fallback: If no agent available, offer callback with time estimate
```

---

## 6. Sensitive Conversations via Voice

### 6.1 Privacy Considerations (Who's Listening)

**Research Finding**: "Companies behind voice assistants often lack transparency regarding data retention policies, creating uncertainty about privacy risks."

**Environmental Awareness**:

At conversation start:
```
"Esta conversacion es confidencial. Si hay alguien cerca que no deberia
escuchar esta informacion, digame 'privacidad' en cualquier momento."
```

**Privacy Mode Triggers**:
- User says "privacidad", "discreto", "alguien escucha"
- Sensitive domain detected (psychology, women's services)
- Financial or personal information being shared

### 6.2 Discrete Mode for Voice

**Discrete Mode Features**:

| Feature | Normal Mode | Discrete Mode |
|---------|-------------|---------------|
| Information delivery | Full details spoken | Abbreviated + SMS |
| Confirmations | Full repetition | "Datos recibidos" only |
| Options presentation | Spoken in full | Numbered only, details via SMS |
| Sensitive data | Spoken | "Envie por mensaje seguro" |

**Activation**:
- User command: "Modo discreto" / "Privacidad"
- Automatic for sensitive domains
- Time-based (public transit hours more likely to need)

### 6.3 Confirmation Without Revealing Information

**Secure Confirmation Patterns**:

```
INSECURE: "Confirmo que su direccion es Calle Reforma 123, Colonia Centro"

SECURE: "Envie su direccion por mensaje. Responda SI cuando la reciba
correctamente, o NO para corregir."
```

**Partial Reveal Pattern**:
```
"Para verificar su identidad, los ultimos 4 digitos de su CURP son [XXXX].
Es correcto?"
```

**Multi-Factor for Sensitive Actions**:
- Voice confirmation + SMS code
- Voice confirmation + app notification
- Voice confirmation + callback verification

### 6.4 Voice-Based Authentication

**Research Finding**: "Voice biometrics provides a second factor of authentication, mitigating the risk of social engineering attacks." However, voice spoofing and injection attacks are emerging threats.

**Voice Authentication Levels**:

| Level | Method | Use Case |
|-------|--------|----------|
| Basic | Known phrase + account lookup | General inquiries |
| Standard | Voiceprint match + security question | Account access |
| High | Voiceprint + OTP via SMS/app | Financial transactions |
| Maximum | Voiceprint + biometric (face/fingerprint on device) | High-value transactions |

**Spoofing Mitigation**:
- Liveness detection (random phrase requests)
- Challenge-response with unpredictable prompts
- Anomaly detection for synthetic voice
- Multi-factor for all sensitive operations

**Privacy-Preserving Authentication**:
- On-device voiceprint storage when possible
- Federated learning for model improvement without data centralization
- Clear consent for voiceprint enrollment
- Option to delete voiceprint data

---

## 7. Technical Requirements

### 7.1 Audio Quality Requirements

**Minimum Specifications**:

| Parameter | Requirement | Rationale |
|-----------|-------------|-----------|
| Sampling Rate | 16 kHz minimum | Full speech bandwidth capture |
| Bit Depth | 16-bit | Standard for voice quality |
| Codec | Opus preferred, fallback to G.711 | Bandwidth efficiency |
| Bandwidth | 256 kbps for 16kHz mono | Reliable transmission |
| Buffer Size | 100-250ms | Balance of speed and accuracy |

**Network Requirements**:
- Jitter buffer: <50ms variation
- Packet loss: <1% for quality
- End-to-end latency: <300ms for natural feel

### 7.2 Latency Thresholds

**Research Finding**: "The 300ms target isn't arbitrary - it's based on natural human conversation timing." The golden target for voice-to-voice interactions is 800ms total latency.

**Component Latency Budgets**:

| Component | Target | Maximum |
|-----------|--------|---------|
| Speech-to-Text (STT) | 100ms | 200ms |
| Intent Processing | 50ms | 100ms |
| LLM Response | 320ms | 500ms |
| Text-to-Speech (TTS) | 90ms | 150ms |
| **Total Voice-to-Voice** | **560ms** | **950ms** |

**User Experience Thresholds**:
- <500ms: Feels instantaneous
- 500-800ms: Natural conversation pace
- 800-1200ms: Acceptable with filler ("Dejeme ver...")
- >1200ms: Noticeable delay, user may re-speak

**Optimization Strategies**:
- Streaming responses (start TTS before full response generated)
- Edge processing for common intents
- Pre-computed responses for frequent queries
- Quantized models (40% latency reduction possible)

### 7.3 Speech-to-Text Accuracy Targets

**Research Finding**: "Healthcare and financial applications typically need sub-3% WER, while general customer service can work with 5-7% WER."

**WER Targets by Domain**:

| Domain | Target WER | Rationale |
|--------|------------|-----------|
| Financial (payments, fines) | <3% | High accuracy for amounts |
| Legal (civil registry) | <3% | Names, dates critical |
| Healthcare referrals | <3% | Medical terminology |
| General services | <5% | Standard accuracy |
| Information queries | <7% | Context helps recovery |

**Accuracy vs. Latency Trade-off**:
- A 95% accurate system at 300ms often beats 98% at 2 seconds
- Correction cycles add 5-10 seconds per misrecognition
- Optimize for "good enough" with fast recovery

### 7.4 Text-to-Speech Naturalness

**Research Finding**: "MOS has a scale of 1-5, with 5 meaning completely natural speech that could pass for a real person." Synthetic speech was indistinguishable from natural speech in intelligibility tests by 2021.

**Target MOS Scores**:

| Dimension | Minimum | Target |
|-----------|---------|--------|
| Overall Naturalness | 4.0 | 4.5+ |
| Prosodic Quality | 4.0 | 4.3+ |
| Intelligibility | 4.5 | 4.8+ |
| Voice Consistency | 4.0 | 4.5+ |

**Voice Selection Criteria for MARIA**:
- Mexican Spanish native accent
- Professional but warm tone
- Clear articulation
- Appropriate for government context
- Gender-neutral option available
- Consistent across all domains

---

## 8. Domain-Specific Voice Guidelines

### 8.1 High-Volume Services (Vehicles, Transport, Water)

**Characteristics**:
- High call volume (60%+ voice for transport)
- Frequent repeat users
- Standard, predictable queries
- Time-sensitive information

**Voice Design**:
```
Efficiency Focus:
- Direct to intent: "Verificacion, renovacion, o consulta de adeudo?"
- Minimal small talk
- Quick confirmations
- Proactive status updates: "Su verificacion vence en 15 dias"
```

**Specific Patterns**:

| Domain | Common Voice Queries | Optimization |
|--------|---------------------|--------------|
| Vehicles | Verification status, fines, renewal | Plate lookup by voice, pre-fetch data |
| Transport | Route info, schedules, card balance | Location-aware, real-time data |
| Water | Bill status, report leak, payment | Account lookup by address |

### 8.2 Sensitive Services (Psychology, Women, Social)

**Characteristics**:
- Emotional complexity
- Privacy paramount
- Crisis potential
- Stigma considerations

**Voice Design**:
```
Empathy Focus:
- Warm, unhurried pace
- Explicit privacy assurance
- No judgment in language
- Easy human escalation
- Crisis detection always active
```

**Domain-Specific Protocols**:

| Domain | Voice Considerations |
|--------|---------------------|
| Psychology | Detect distress, slower pace, warmth, crisis line integration |
| Women's Services | Code words for safety, discrete mode default, emergency protocols |
| Social Services | Dignity-preserving language, no bureaucratic coldness, patience |

**Safety Word System** (Women's Services):
```
User can say: "[Code word]" at any time
System responds: Normal-sounding response while triggering:
- Silent alert to support staff
- Recording activation (with consent framework)
- Location services (if enabled)
- Prepared safety resources ready
```

### 8.3 Complex Services (Civil Registry, Housing)

**Characteristics**:
- Multi-step processes
- Document requirements
- Legal implications
- Less frequent but high-stakes

**Voice Design**:
```
Guidance Focus:
- Clear step-by-step instructions
- Confirmation at each stage
- SMS/email backup of requirements
- Human available for exceptions
```

**Complexity Management**:

```
Civil Registry (Birth Certificate Example):

Voice: "Para obtener un acta de nacimiento necesita:
       Primero, su identificacion oficial.
       Segundo, comprobante de domicilio.
       Tercero, el pago de derechos.

       Le envio esta lista por mensaje. Tiene alguna pregunta sobre
       los requisitos, o prefiere agendar una cita?"
```

**Document Guidance Pattern**:
- List requirements (max 3 at a time)
- Offer SMS confirmation
- Check for questions
- Provide appointment option
- Human escalation for exceptions

---

## 9. IVR Migration Strategy

### 9.1 Phased Approach

**Research Finding**: "A phased, business-driven migration minimizes risk and maximizes impact." Start with high-volume, predictable use cases.

**Migration Phases for MARIA**:

| Phase | Timeline | Domains | Capability |
|-------|----------|---------|------------|
| 1 | Months 1-3 | Vehicles, Water, Transport | Simple queries, status checks |
| 2 | Months 4-6 | All 13 domains | FAQs, appointment scheduling |
| 3 | Months 7-9 | Full platform | Transactions, complex flows |
| 4 | Months 10-12 | Optimization | Advanced features, full voice |

### 9.2 Hybrid Strategy

**Initial Hybrid Model**:
```
Caller -> Greeting -> Intent Detection
                      |
                      v
              [Confidence Check]
                /           \
            High             Low
              |               |
              v               v
        Voice AI         IVR Fallback
        handles          "Press 1 for..."
```

**Gradual Handoff**:
- Week 1-4: 20% to Voice AI, 80% IVR
- Month 2: 40% Voice AI
- Month 3: 60% Voice AI
- Month 4+: 80% Voice AI, IVR as fallback

### 9.3 User Adaptation Support

**Bridge Patterns for IVR-Familiar Users**:
```
"Puede decirme lo que necesita, o si prefiere, presione 1 para vehiculos,
2 para agua, 3 para otros servicios"
```

**Training Users**:
- First interactions offer both voice and DTMF
- Successful voice interactions reduce DTMF prompts
- Never remove DTMF entirely (accessibility)

---

## 10. Quality Assurance Framework

### 10.1 Key Performance Indicators

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task Completion Rate | >85% | Successful intent resolution |
| First Contact Resolution | >75% | No repeat calls needed |
| Average Handle Time | <3 min for simple, <5 for complex | End-to-end voice interaction |
| Human Escalation Rate | <15% | Transfers to human agents |
| User Satisfaction (CSAT) | >4.2/5 | Post-call survey |
| ASR Accuracy | >95% | Word recognition rate |
| Latency (P95) | <1200ms | Voice-to-voice response |

### 10.2 Continuous Improvement

**Feedback Loops**:
1. Failed interaction analysis (weekly)
2. Low-confidence pattern review (weekly)
3. Human escalation reason categorization (weekly)
4. User satisfaction correlation (monthly)
5. A/B testing of conversation patterns (ongoing)

**ASR Improvement Cycle**:
```
1. Collect anonymized failed transcriptions
2. Identify patterns (accents, terms, noise)
3. Retrain with corrected labels
4. Deploy updated model
5. Monitor WER improvement
```

---

## 11. Ethical and Compliance Considerations

### 11.1 Regulatory Compliance (Mexico)

- **LFPDPPP** (Data Protection): Voice recordings are personal data
- **Transparency**: Disclose AI nature at conversation start
- **Consent**: Explicit for voiceprint enrollment, implicit for service use
- **Data Retention**: Minimum necessary, clear deletion policies
- **Access Rights**: Users can request conversation transcripts

### 11.2 EU Considerations (Reference)

**Research Finding**: "The European Union banned emotion AI in workplaces and educational settings as of August 2024, with exceptions for medical and safety applications."

**Best Practice Adoption**:
- Limit emotion detection to service improvement only
- No discriminatory use of emotional data
- Transparent about emotion detection capabilities
- User opt-out option where feasible

### 11.3 Disclosure Requirements

**Opening Disclosure**:
```
"Hola, soy MARIA, la asistente virtual del Gobierno de Queretaro.
Esta llamada puede ser grabada para mejorar el servicio.
En que puedo ayudarle?"
```

**For Voiceprint Enrollment**:
```
"Para acceder a servicios personalizados, podemos crear un perfil de voz
seguro. Esto nos permite identificarlo sin preguntas de seguridad.
Acepta que guardemos su perfil de voz? Puede eliminarlo en cualquier momento."
```

---

## Sources

### Voice Conversation Design
- [Lollypop Studio - Voice User Interface Design Best Practices 2025](https://lollypop.design/blog/2025/august/voice-user-interface-design-best-practices/)
- [AufaitUX - Voice User Interface Design Best Practices](https://www.aufaitux.com/blog/voice-user-interface-design-best-practices/)
- [Cartesia - State of Voice AI 2024](https://cartesia.ai/blog/state-of-voice-ai-2024)
- [Bland AI - What Is Conversational AI Design](https://www.bland.ai/blogs/conversational-ai-design)
- [Botpress - Conversational AI Design in 2026](https://botpress.com/blog/conversation-design)
- [AssemblyAI - AI Voice Agents 2026](https://www.assemblyai.com/blog/ai-voice-agents)

### Spanish Language Voice AI
- [ElevenLabs - Spanish Text to Speech](https://elevenlabs.io/text-to-speech/spanish)
- [ElevenLabs - Mexican Accent Voice Generator](https://elevenlabs.io/text-to-speech/mexican-accent)
- [Murf AI - Spanish Text to Speech](https://murf.ai/text-to-speech/spanish)
- [ReadSpeaker - Mexican Spanish TTS](https://www.readspeaker.com/languages-voices/mexican-spanish/)
- [Resemble AI - Spanish TTS](https://www.resemble.ai/spanish-tts/)

### Emotional Intelligence
- [GaslightingCheck - How AI Detects Vocal Emotion](https://www.gaslightingcheck.com/blog/how-ai-detects-vocal-emotion-across-cultures)
- [Dialzara - Voice Sentiment Analysis Techniques](https://dialzara.com/blog/top-7-sentiment-analysis-techniques-for-voice-ai)
- [NiCE - Emotion Detection in Voice AI](https://www.nice.com/glossary/emotion-detection-in-voice-ai)
- [Tavus - Emotional AI Complete Guide 2025](https://www.tavus.io/post/emotional-ai)
- [Chanl AI - Emotional Intelligence in Voice AI](https://www.chanl.ai/blog/emotional-intelligence-voice-ai-sentiment)

### Accessibility
- [Accessibility Checker - Text-to-Speech Accessibility 2025](https://www.accessibilitychecker.org/blog/text-to-speech-accessibility/)
- [WebAbility - Voice Control and Accessibility](https://www.webability.io/blog/voice-control-and-accessibility-the-rise-of-voice-activated-interfaces)
- [Inaza - Accessibility in AI Customer Service](https://www.inaza.com/blog/accessibility-in-ai-customer-service-wcag-for-voice-chat)
- [W3C WAI - Speech Recognition](https://www.w3.org/WAI/perspective-videos/voice/)
- [RubyRoid Labs - WCAG 3.0 Updates](https://rubyroidlabs.com/blog/2025/10/how-to-prepare-for-wcag-3-0/)

### Error Handling & Barge-In
- [Hamming AI - Voice Agent Quality Assurance](https://hamming.ai/resources/guide-to-ai-voice-agents-quality-assurance)
- [BeConversive - Common Voice AI Challenges](https://www.beconversive.com/blog/voice-ai-challenges)
- [SparkCo - Master Voice Agent Barge-In Detection](https://sparkco.ai/blog/master-voice-agent-barge-in-detection-handling)
- [Gnani AI - Real-Time Barge-In AI](https://www.gnani.ai/resources/blogs/real-time-barge-in-ai-for-voice-conversations-31347)
- [IDT Express - Barge-In and Natural Conversation](https://www.idtexpress.com/blog/barge-in-interruptions-and-natural-conversation-making-ai-sound-human-on-inbound-calls/)

### IVR Migration
- [PTP Inc - Modernizing Voice Platforms](https://ptpinc.com/ai/modernizing-voice-platforms/)
- [Welco AI - AI Voice Agents vs IVR Systems](https://welco.ai/blog/ai-voice-agents-vs-ivr-systems/)
- [Vonage - Combining AI and IVR](https://www.vonage.com/resources/articles/ai-ivr/)
- [Teneo AI - Future of IVR Software 2025](https://www.teneo.ai/blog/the-future-of-interactive-voice-response-ivr-software-in-2025)
- [NoJitter - AI Taking Over Phone Calls](https://www.nojitter.com/contact-centers/goodbye-ivr-hell-smart-ai-will-take-over-phone-calls)

### Security & Authentication
- [RINF Tech - Voice Recognition Security and Privacy](https://www.rinf.tech/voice-recognition-and-security-balancing-convenience-and-privacy/)
- [Impala Intech - Voice AI Privacy Risks](https://impalaintech.com/blog/voice-ai-security-concern/)
- [Parloa - Voice Biometrics Walkthrough](https://www.parloa.com/knowledge-hub/voice-biometrics/)
- [NiCE - Voice Biometrics for Contact Centers](https://www.nice.com/info/voice-biometrics-for-contact-centers)
- [Canadian Cyber Security Centre - Voice Assistant Security](https://www.cyber.gc.ca/en/guidance/security-considerations-voice-activated-digital-assistants-itsap70013)

### Technical Requirements
- [AssemblyAI - The 300ms Rule for Voice AI](https://www.assemblyai.com/blog/low-latency-voice-ai)
- [Hamming AI - Voice Agent Evaluation Metrics](https://hamming.ai/resources/voice-agent-evaluation-metrics-guide)
- [Hamming AI - Best Voice Agent Stack](https://hamming.ai/resources/best-voice-agent-stack)
- [NextLevel AI - Best Speech to Text Models 2025](https://nextlevel.ai/best-speech-to-text-models/)
- [Dialzara - AI Voice Hardware Requirements](https://dialzara.com/blog/ai-voice-hardware-requirements-compatibility-guide)

### Human Escalation
- [Leaping AI - Voicebot Escalation to Humans](https://leapingai.com/blog/can-a-voicebot-escalate-calls-to-humans)
- [JustCall - AI Voice Agent Escalation Frameworks](https://justcall.io/blog/ai-voice-agent-escalation.html)
- [Replicant - Setting Effective AI Escalation Rules](https://www.replicant.com/blog/when-to-hand-off-to-a-human-how-to-set-effective-ai-escalation-rules)
- [Robylon AI - AI Handoffs to Humans](https://www.robylon.ai/blog/smarter-ai-escalations-customer-support)

### Elderly Users & Accessibility
- [Governa AI - Voice Assistants for Seniors](https://www.governa.ai/blog-posts/voice-assistants-a-seniors-new-best-friend)
- [Aging and Health Technology Watch - Voice AI for Older Adults](https://www.ageinplacetech.com/category/category-tags/voice-firstaivoice-assistants)
- [Springer - Voice Assistants for Older People Mobility](https://link.springer.com/article/10.1007/s00146-024-01865-8)
- [PMC - Older People Voice Interactions with Smart Assistants](https://pmc.ncbi.nlm.nih.gov/articles/PMC11135128/)

### Crisis Detection
- [Nature - Suicide Prediction Using Voice Recordings and AI](https://www.nature.com/articles/s41598-025-08639-2)
- [New Atlas - AI Voice Analysis for Suicide Prevention](https://newatlas.com/technology/ai-emotion-speech-suicide-prevention/)
- [PMC - Detection of Suicide Risk Using Vocal Characteristics](https://pmc.ncbi.nlm.nih.gov/articles/PMC11041425/)
- [Nature - NLP for Mental Health Crisis Detection](https://www.nature.com/articles/s41746-023-00951-3)

### TTS Quality
- [OpenReview - Critical Analysis of MOS Test Methodology](https://openreview.net/pdf?id=bnVBXj-mOc)
- [Way With Words - MOS Ratings for TTS Models](https://waywithwords.net/landing/mean-opinion-score-ratings-2/)
- [VoiceMOS Challenge 2024](https://www.researchgate.net/publication/384075048_The_T05_System_for_The_VoiceMOS_Challenge_2024)

---

*Document prepared for MARIA - Gobierno de Queretaro AI Platform*
*Research conducted: February 2026*
