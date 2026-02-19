# Conversation Flow Design Patterns for Government AI

> **Research Document**: Comprehensive conversation design patterns for the Gobierno de Queretaro AI platform
> **Version**: 1.0
> **Date**: February 2026
> **Scope**: 13 government service domains

---

## Executive Summary

This document synthesizes current best practices (2024-2026) in conversational AI design for government services. It provides actionable templates, branching logic patterns, and recovery strategies specifically tailored for citizen-facing AI assistants. The patterns address the unique requirements of government services including accessibility, multilingual support, compliance, and trust-building.

---

## 1. Dialog Structure Principles

### 1.1 Turn-Taking Patterns

Effective government chatbots follow structured turn-taking that balances efficiency with clarity:

**Single-Turn Pattern** (Simple queries)
```
User: What are the office hours?
Bot: [Direct answer with action offer]
     "Nuestras oficinas estan abiertas de lunes a viernes, 8:00 AM - 4:00 PM.
      Quieres que te comparta la direccion o agendar una cita?"
```

**Multi-Turn Pattern** (Complex tasks)
```
Turn 1: User intent declaration
Turn 2: Bot clarification/validation
Turn 3: User confirmation/addition
Turn 4: Bot action + status
Turn 5: Bot follow-up offer
```

**Key Principles:**
- **Keep responses concise**: Government users often have specific needs; avoid verbose explanations
- **One question per turn**: Never ask multiple questions simultaneously
- **Acknowledge before asking**: Always confirm understanding before requesting more information
- **Offer escape routes**: Every turn should have a path to human assistance

### 1.2 Information Gathering Strategies

#### Progressive Disclosure Pattern
Collect information incrementally, revealing complexity only when necessary:

```
Level 1: Basic identification
  "Para ayudarte mejor, necesito algunos datos.
   Cual es tu nombre completo?"

Level 2: Service-specific details (only if needed)
  "Gracias, [nombre]. Para [servicio], necesito verificar:
   Cual es tu CURP o INE?"

Level 3: Transaction-specific (only for complex transactions)
  "Para completar [tramite especifico], tambien necesitare:
   - Comprobante de domicilio
   - [Documento adicional]"
```

#### Slot-Filling Pattern
Modern LLM-based systems can extract multiple entities from natural language:

```yaml
# Slot Schema Definition
appointment_booking:
  required_slots:
    - name: string
    - service_type: enum [consulta, tramite, queja]
    - preferred_date: date
    - contact_phone: string
  optional_slots:
    - preferred_time: time
    - additional_notes: string

# Proactive Extraction Example
User: "Quiero una cita para el proximo martes para renovar mi licencia,
       soy Juan Perez del tel 442-123-4567"

Bot extracts:
  - name: "Juan Perez"
  - service_type: "tramite" (inferred from "renovar licencia")
  - preferred_date: [next Tuesday date]
  - contact_phone: "442-123-4567"

Bot responds:
  "Perfecto, Juan. Tengo tu cita para renovacion de licencia el [fecha].
   A que hora te conviene mejor? Tenemos disponibilidad a las 9:00, 11:00 y 14:00."
```

### 1.3 Confirmation Approaches

#### Explicit Confirmation (High-Stakes Actions)
Use for irreversible or important transactions:

```
Bot: "Voy a registrar tu queja sobre [tema] en [dependencia].

      Resumen:
      - Asunto: [descripcion breve]
      - Fecha del incidente: [fecha]
      - Ubicacion: [lugar]

      Una vez registrada, recibiras un numero de folio.
      Confirmas que los datos son correctos?"

      [Confirmar y enviar] [Modificar datos] [Cancelar]
```

#### Implicit Confirmation (Low-Stakes Actions)
Use for reversible or informational queries:

```
Bot: "Entiendo que buscas informacion sobre [tema].
      Aqui tienes los detalles: [informacion]

      Hay algo mas que pueda ayudarte con [tema relacionado]?"
```

#### Undo Pattern (Preferred for Routine Actions)
Instead of asking for confirmation, allow immediate reversal:

```
Bot: "Listo! Tu cita ha sido agendada para [fecha/hora].
      [Deshacer] | [Ver detalles] | [Agregar al calendario]"

      (Undo available for 30 seconds)
```

**Avoid "Yes/No" Ambiguity:**
Instead of: "Quieres continuar? [Si] [No]"
Use: "[Continuar con registro] [Volver al menu] [Hablar con agente]"

### 1.4 Context Management Architecture

```yaml
session_state:
  # Temporary - cleared at session end
  current_intent: string
  collected_slots: object
  conversation_turn: number
  last_bot_action: string
  pending_clarification: boolean

user_state:
  # Persistent - stored across sessions
  user_id: string
  verified_identity: boolean
  language_preference: "es" | "en" | "indigenous"
  accessibility_needs: string[]
  previous_services: string[]
  open_tickets: string[]

context_window:
  # LLM context management
  strategy: "sliding_window_with_summary"
  recent_turns: 10  # Full detail
  older_turns: "compressed_summary"
  max_tokens: 4000

  # Priority context injection
  always_include:
    - user_identity (if verified)
    - current_service_domain
    - any open tickets/cases
```

---

## 2. Core Flow Templates

### 2.1 Information Query Flow

**Scenario**: Citizen needs information about a government service

```
┌─────────────────────────────────────────────────────────────┐
│                    INFORMATION QUERY FLOW                    │
└─────────────────────────────────────────────────────────────┘

[START] User asks question
    │
    ▼
[INTENT CLASSIFICATION]
    │
    ├── High Confidence (>80%)
    │       │
    │       ▼
    │   [PROVIDE INFORMATION]
    │       │
    │       ▼
    │   [OFFER RELATED ACTIONS]
    │       "Esta informacion te fue util?
    │        Tambien puedo ayudarte a:
    │        - Agendar cita
    │        - Descargar formato
    │        - Hablar con especialista"
    │       │
    │       └──► [END or CONTINUE]
    │
    ├── Medium Confidence (50-80%)
    │       │
    │       ▼
    │   [CLARIFICATION]
    │       "Encontre informacion sobre [tema A] y [tema B].
    │        Cual te interesa?"
    │        [Opcion A] [Opcion B] [Otro tema]
    │       │
    │       └──► [PROVIDE INFORMATION]
    │
    └── Low Confidence (<50%)
            │
            ▼
        [DISAMBIGUATION]
            "No estoy seguro de entender tu pregunta.
             Puedes elegir una opcion o reformular:
             - [Sugerencia 1]
             - [Sugerencia 2]
             - [Escribir de nuevo]
             - [Hablar con agente]"
            │
            └──► [RETRY or ESCALATE]
```

**Sample Dialog:**

```
User: "Como renuevo mi licencia?"

Bot:  "Para renovar tu licencia de conducir en Queretaro, necesitas:

       Requisitos:
       1. Licencia anterior (o denuncia de extravio)
       2. INE o pasaporte vigente
       3. Comprobante de domicilio reciente
       4. Pago de derechos ($850 MXN aprox.)

       El proceso toma aproximadamente 30 minutos.

       Te ayudo con algo mas?
       [Agendar cita] [Ver ubicaciones] [Simular costo exacto]"
```

### 2.2 Transaction Flow

**Scenario**: Citizen needs to complete a government procedure

```
┌─────────────────────────────────────────────────────────────┐
│                     TRANSACTION FLOW                         │
└─────────────────────────────────────────────────────────────┘

[START] User expresses transaction intent
    │
    ▼
[ELIGIBILITY CHECK]
    "Antes de comenzar, verificare que cumplas
     los requisitos para [tramite]."
    │
    ├── Eligible
    │       │
    │       ▼
    │   [GATHER REQUIREMENTS]
    │       │
    │       ├── Documents needed?
    │       │       "Para este tramite necesitaras:
    │       │        □ [Documento 1]
    │       │        □ [Documento 2]
    │       │        Tienes estos documentos a la mano?"
    │       │
    │       ├── Information needed?
    │       │       [Progressive slot-filling]
    │       │
    │       └── Payment required?
    │               "El costo de este tramite es $[monto].
    │                Metodos de pago: [opciones]"
    │       │
    │       ▼
    │   [VALIDATE INPUTS]
    │       │
    │       ├── Valid
    │       │       │
    │       │       ▼
    │       │   [CONFIRM TRANSACTION]
    │       │       "Resumen de tu solicitud:
    │       │        [detalles]
    │       │        Confirmas para proceder?"
    │       │       [Confirmar] [Modificar] [Cancelar]
    │       │       │
    │       │       ▼
    │       │   [EXECUTE]
    │       │       │
    │       │       ├── Success
    │       │       │       │
    │       │       │       ▼
    │       │       │   [CONFIRM COMPLETION]
    │       │       │       "Tu tramite ha sido registrado!
    │       │       │        Folio: [numero]
    │       │       │        Siguiente paso: [instruccion]
    │       │       │        Tiempo estimado: [plazo]"
    │       │       │
    │       │       └── Failure
    │       │               │
    │       │               ▼
    │       │           [ERROR RECOVERY]
    │       │               (See Section 4)
    │       │
    │       └── Invalid
    │               │
    │               ▼
    │           [CORRECTION REQUEST]
    │               "Hay un problema con [campo]:
    │                [explicacion del error]
    │                Por favor corrige este dato."
    │
    └── Not Eligible
            │
            ▼
        [EXPLAIN + ALTERNATIVES]
            "No puedes realizar este tramite porque:
             [razon]

             Alternativas:
             - [Opcion 1]
             - [Opcion 2]
             - Hablar con asesor para casos especiales"
```

**Sample Dialog:**

```
User: "Quiero registrar una queja sobre el transporte publico"

Bot:  "Entendido. Voy a ayudarte a registrar una queja sobre
       transporte publico con AMEQ.

       Primero necesito algunos datos:
       Cual es tu nombre completo?"

User: "Maria Garcia Lopez"

Bot:  "Gracias, Maria. Ahora cuentame:
       Que paso exactamente? Describe la situacion brevemente."

User: "El camion de la ruta 45 paso de largo en mi parada
       esta manana aunque hice la senal"

Bot:  "Lamento que hayas tenido esa experiencia.

       Registro:
       - Ruta: 45
       - Tipo: Camion no se detuvo en parada
       - Fecha: Hoy, [fecha]

       Para completar la queja, necesito:
       1. Hora aproximada del incidente?
       2. Nombre de la parada o ubicacion?
       3. Numero economico del camion (si lo recuerdas)?"

User: "Fue como a las 7:30am en la parada de Plaza del Sol,
       no vi el numero"

Bot:  "Perfecto. Tengo toda la informacion:

       RESUMEN DE QUEJA
       ─────────────────
       Ciudadano: Maria Garcia Lopez
       Ruta: 45
       Incidente: Unidad no se detuvo en parada
       Fecha: [fecha] aprox. 7:30 AM
       Ubicacion: Parada Plaza del Sol
       Numero economico: No identificado

       Al registrar esta queja, AMEQ investigara el caso
       y te contactara en maximo 5 dias habiles.

       [Registrar queja] [Agregar detalles] [Cancelar]"

User: [clicks "Registrar queja"]

Bot:  "Tu queja ha sido registrada exitosamente!

       Folio: AMEQ-2026-00123

       Guarda este numero para dar seguimiento.
       Te enviaremos actualizaciones por WhatsApp.

       Hay algo mas en lo que pueda ayudarte?
       [Consultar estado de queja] [Nueva consulta] [Finalizar]"
```

### 2.3 Complaint/Issue Flow

**Scenario**: Citizen needs to report a problem or file a complaint

```
┌─────────────────────────────────────────────────────────────┐
│                   COMPLAINT/ISSUE FLOW                       │
└─────────────────────────────────────────────────────────────┘

[START] User reports issue
    │
    ▼
[ACKNOWLEDGE + EMPATHIZE]
    "Lamento escuchar sobre [situacion].
     Voy a ayudarte a registrar esto correctamente."
    │
    ▼
[CATEGORIZE]
    │
    ├── Clear category
    │       │
    │       ▼
    │   [GATHER DETAILS]
    │       "Para investigar esto, necesito saber:
    │        - Cuando ocurrio?
    │        - Donde exactamente?
    │        - Tienes fotos o evidencia?"
    │
    └── Unclear category
            │
            ▼
        [CLASSIFY WITH OPTIONS]
            "Para canalizar tu reporte correctamente:
             Esto es sobre:
             [Servicio publico] [Funcionario] [Infraestructura]
             [Seguridad] [Otro]"
    │
    ▼
[SEVERITY ASSESSMENT]
    │
    ├── Emergency/Urgent
    │       │
    │       ▼
    │   [IMMEDIATE ESCALATION]
    │       "Esta situacion requiere atencion inmediata.
    │        Voy a conectarte con un agente ahora.
    │        Mientras tanto: [instrucciones de emergencia]"
    │
    └── Standard
            │
            ▼
        [CREATE TICKET]
            │
            ▼
        [SET EXPECTATIONS]
            "Tu reporte sera revisado por [dependencia].
             Tiempo de respuesta: [plazo]
             Te notificaremos por [canal]"
            │
            ▼
        [PROVIDE REFERENCE]
            "Tu numero de folio es: [ID]
             Guardalo para consultar el estado.

             Quieres que te envie un resumen por correo?"
```

**Empathy Phrases for Government Context:**

```yaml
empathy_library:
  acknowledgment:
    - "Entiendo tu frustracion, [nombre]."
    - "Lamento que hayas tenido esta experiencia."
    - "Gracias por reportar esto; es importante saberlo."
    - "Comprendo que esto ha sido molesto."

  reassurance:
    - "Vamos a revisar tu caso con atencion."
    - "Tu reporte ayuda a mejorar nuestros servicios."
    - "Nos aseguraremos de que se atienda."
    - "Estamos aqui para ayudarte a resolver esto."

  urgency_acknowledgment:
    - "Veo que es urgente. Priorizare tu caso."
    - "Entiendo la importancia de esto para ti."
    - "Voy a canalizar esto de inmediato."
```

### 2.4 Status Check Flow

**Scenario**: Citizen checks on existing request/ticket

```
┌─────────────────────────────────────────────────────────────┐
│                    STATUS CHECK FLOW                         │
└─────────────────────────────────────────────────────────────┘

[START] User asks about status
    │
    ▼
[IDENTIFICATION]
    │
    ├── User already verified
    │       │
    │       ▼
    │   [RETRIEVE RECORDS]
    │       "Encontre [N] tramites activos a tu nombre:
    │        1. [Tramite 1] - [estado]
    │        2. [Tramite 2] - [estado]
    │        Cual te interesa revisar?"
    │
    ├── Has folio number
    │       │
    │       ▼
    │   [LOOKUP BY FOLIO]
    │       │
    │       ├── Found
    │       │       "Estado de tu tramite [folio]:
    │       │        Tipo: [descripcion]
    │       │        Estado: [En proceso/Completado/Requiere accion]
    │       │        Ultimo movimiento: [fecha]
    │       │        Siguiente paso: [accion]"
    │       │
    │       └── Not found
    │               "No encontre un tramite con ese folio.
    │                Verifica el numero o intenta con:
    │                [Buscar por CURP] [Buscar por fecha]"
    │
    └── No identifier
            │
            ▼
        [REQUEST IDENTIFICATION]
            "Para buscar tu tramite, necesito:
             - Tu numero de folio, o
             - Tu CURP para buscar todos tus tramites"
```

---

## 3. Disambiguation Patterns

### 3.1 "Did You Mean X or Y?" Pattern

Use when confidence is split between 2-3 options:

```
User: "Quiero sacar mi licencia"

Bot:  "Hay varios tipos de licencia. Te refieres a:

       [Licencia de conducir]
       Para manejar vehiculos particulares

       [Licencia de manejo tipo A]
       Para transporte publico de pasajeros

       [Licencia comercial]
       Para transporte de carga

       [Otro tipo de licencia]"
```

### 3.2 Confidence-Based Clarification

```yaml
clarification_strategy:
  high_confidence: # >85%
    action: "proceed_with_assumption"
    pattern: |
      "Entiendo que necesitas [servicio inferido].
       [Proceder con flujo]
       (Si buscabas otra cosa, dimelo)"

  medium_confidence: # 60-85%
    action: "soft_clarification"
    pattern: |
      "Parece que necesitas [servicio principal].
       Es correcto?
       [Si, continuar] [No, busco otra cosa]"

  low_confidence: # 40-60%
    action: "options_with_context"
    pattern: |
      "Puedo ayudarte con varias cosas relacionadas:
       - [Opcion 1]: [breve descripcion]
       - [Opcion 2]: [breve descripcion]
       - [Opcion 3]: [breve descripcion]
       Cual necesitas?"

  very_low_confidence: # <40%
    action: "open_clarification"
    pattern: |
      "No estoy seguro de entender.
       Puedes decirme mas sobre lo que necesitas?

       O elige un tema:
       [Tramites] [Quejas] [Informacion] [Hablar con agente]"
```

### 3.3 Progressive Disclosure Pattern

Start with broad categories, narrow down:

```
[Level 1 - Domain]
Bot: "En que area puedo ayudarte?
      [Agua y drenaje] [Transporte] [Tramites vehiculares]
      [Educacion] [Vivienda] [Otro]"

User: [clicks "Tramites vehiculares"]

[Level 2 - Service Type]
Bot: "Tramites vehiculares. Que necesitas?
      [Licencia de conducir] [Placas y registro]
      [Verificacion vehicular] [Tenencias] [Otro]"

User: [clicks "Licencia de conducir"]

[Level 3 - Specific Action]
Bot: "Licencia de conducir. Selecciona:
      [Primera vez] [Renovacion] [Reposicion]
      [Cambio de tipo] [Consultar requisitos]"
```

### 3.4 Smart Defaults Pattern

Use user history and common patterns to suggest defaults:

```
# Returning user
Bot: "Hola de nuevo, [nombre]!
      La ultima vez ayudamos con tu tramite de licencia.

      Vienes por lo mismo o algo diferente?
      [Seguimiento de licencia] [Otro tramite]"

# Common query inference
User: "horarios"

Bot: "Estos son los horarios mas consultados:

      Oficinas de Atencion Ciudadana:
      Lun-Vie 8:00 - 16:00

      Te refieres a otro servicio?
      [Modulo de licencias] [CEA (Agua)] [AMEQ (Transporte)]"
```

### 3.5 Entity Disambiguation

When the same term could mean different things:

```
User: "Necesito un certificado"

Bot: "Que tipo de certificado necesitas?

      [Certificado de no adeudo]
      Demuestra que no tienes deudas con el gobierno

      [Certificado de residencia]
      Comprueba tu domicilio en el estado

      [Constancia de situacion fiscal]
      Documento del SAT (te redirijo)

      [Certificado de estudios]
      Tramite con USEBEQ

      [Otro certificado]"
```

---

## 4. Error Recovery Patterns

### 4.1 Misunderstanding Recovery

```
┌─────────────────────────────────────────────────────────────┐
│               MISUNDERSTANDING RECOVERY                      │
└─────────────────────────────────────────────────────────────┘

[Bot gives wrong answer]
    │
    ▼
[User indicates error]
    "No, eso no es lo que pregunte"
    │
    ▼
[ACKNOWLEDGE + RESET]
    "Disculpa, parece que no entendi bien.
     Dejame intentar de nuevo.

     Puedes decirme de otra forma que necesitas?
     O selecciona una opcion:
     [Opcion A] [Opcion B] [Describir diferente] [Agente]"
```

**Recovery Phrase Library:**

```yaml
misunderstanding_recovery:
  first_attempt:
    - "Parece que no entendi bien. Puedes reformular tu pregunta?"
    - "Disculpa, creo que me confundi. A que te refieres exactamente?"
    - "Quiero asegurarme de ayudarte correctamente. Puedes darme mas detalles?"

  second_attempt:
    - "Sigo teniendo dificultad para entender. Te ofrezco estas opciones:"
    - "Dejame mostrarte los temas en los que puedo ayudarte:"

  third_attempt:
    - "Creo que es mejor que hables con un agente humano que pueda ayudarte mejor."
    - "Voy a conectarte con un especialista para asegurar que recibas la ayuda correcta."
```

### 4.2 API Failure Handling

```
┌─────────────────────────────────────────────────────────────┐
│                   API FAILURE HANDLING                       │
└─────────────────────────────────────────────────────────────┘

[API Call]
    │
    ├── Success ──► [Continue flow]
    │
    ├── Timeout
    │       │
    │       ▼
    │   "La consulta esta tomando mas tiempo de lo normal.
    │    [Esperar un poco mas] [Intentar de nuevo] [Regresar despues]"
    │
    ├── Service Unavailable
    │       │
    │       ▼
    │   "El sistema de [servicio] no esta disponible en este momento.
    │
    │    Alternativas:
    │    - Intenta de nuevo en 30 minutos
    │    - Llama al [telefono] para asistencia directa
    │    - [Recibir notificacion cuando este disponible]"
    │
    └── Partial Data
            │
            ▼
        "Pude obtener parte de la informacion:
         [datos disponibles]

         Para los detalles completos, puedes:
         [Reintentar] [Ver informacion parcial] [Contactar soporte]"
```

### 4.3 Incomplete Information Handling

```
[Required slot missing after multiple attempts]
    │
    ▼
[EXPLAIN REQUIREMENT]
    "Necesito [dato] para poder continuar porque:
     [razon clara - ej: 'es requerido por ley para este tramite']

     Si no tienes este dato ahora:
     [Guardar progreso y continuar despues]
     [Obtener ayuda para conseguir el dato]
     [Hablar con agente]"
```

### 4.4 Invalid Input Handling

```yaml
invalid_input_responses:
  format_error:
    curp:
      message: "El CURP debe tener 18 caracteres (letras y numeros).
                El que ingresaste tiene [N]. Verifica e intenta de nuevo."
      example: "Ejemplo: GARC850101HQRRRL09"

    phone:
      message: "Ingresa un telefono de 10 digitos sin espacios ni guiones."
      example: "Ejemplo: 4421234567"

    email:
      message: "El correo no parece valido. Asegurate de incluir @ y el dominio."
      example: "Ejemplo: tucorreo@gmail.com"

    date:
      message: "Ingresa la fecha en formato dia/mes/ano."
      example: "Ejemplo: 15/03/2026"

  out_of_range:
    date_past:
      message: "La fecha no puede ser en el pasado para este tramite."
    date_too_far:
      message: "Solo puedo agendar citas hasta [X] dias en el futuro."
    amount_exceeded:
      message: "El monto maximo permitido es [cantidad]."

  not_found:
    folio:
      message: "No encontre un tramite con el folio [numero].
                Verifica que este correcto o intenta:
                [Buscar por CURP] [Buscar por fecha]"
```

### 4.5 Loop Prevention

Prevent frustrating repetitive loops:

```python
# Pseudocode for loop detection
loop_detection:
  max_clarification_attempts: 2
  max_invalid_input_attempts: 3
  max_same_intent_failures: 2

  on_loop_detected:
    action: "escalate_or_pivot"
    message: |
      "Parece que estamos teniendo dificultad con esto.

       Prefieres:
       [Hablar con un agente]
       [Empezar de nuevo]
       [Recibir ayuda por otro canal]"
```

---

## 5. Context Management

### 5.1 Session State Structure

```typescript
interface SessionState {
  // Identification
  sessionId: string;
  startTime: Date;
  channel: 'whatsapp' | 'web' | 'voice';

  // Conversation tracking
  currentDomain: string | null;  // e.g., 'transporte', 'agua'
  currentIntent: string | null;  // e.g., 'file_complaint', 'check_status'
  conversationPhase: 'greeting' | 'information_gathering' | 'execution' | 'confirmation' | 'closing';

  // Slot filling
  collectedSlots: Record<string, any>;
  requiredSlots: string[];
  pendingSlot: string | null;

  // Error tracking
  clarificationAttempts: number;
  lastErrorType: string | null;

  // Human handoff
  escalationRequested: boolean;
  escalationReason: string | null;

  // Timestamps
  lastInteractionTime: Date;
  turnCount: number;
}
```

### 5.2 Cross-Turn Reference Patterns

```
# Pronoun Resolution
User: "Quiero renovar mi licencia"
Bot: [Provides renewal information]
User: "Cuanto cuesta?"  <-- "it" refers to license renewal
Bot: "La renovacion de licencia cuesta $850 MXN aproximadamente."

# Context Carryover
User: "Horarios de la oficina de tramites vehiculares"
Bot: [Provides hours]
User: "Y la direccion?"  <-- implicit: same office
Bot: "La direccion de la oficina de Tramites Vehiculares es: [direccion]"

# Topic Continuation
User: "Informacion sobre becas"
Bot: [Provides scholarship info]
User: "Cuales son los requisitos?"  <-- implicit: for scholarships
Bot: "Los requisitos para las becas son: [lista]"
```

**Implementation:**

```yaml
context_resolution:
  # Track recent entities
  recent_entities:
    max_items: 5
    retention: "until_topic_change"

  # Implicit reference rules
  implicit_references:
    "cuanto cuesta": resolve_to_last_service
    "la direccion": resolve_to_last_location_context
    "los requisitos": resolve_to_last_service_or_document
    "cuando": resolve_to_last_event_or_deadline
    "donde": resolve_to_last_office_or_service

  # Topic change detection
  topic_change_signals:
    - explicit_new_intent
    - "otra cosa"
    - "tambien quiero"
    - "ahora necesito"
    - significant_entity_change
```

### 5.3 User Profile Integration

```yaml
user_profile:
  # Basic info (from authentication)
  identity:
    name: string
    curp: string (masked)
    verified: boolean

  # Preferences (learned over time)
  preferences:
    language: "es" | "en"
    formality: "formal" | "casual"
    channel_preference: "whatsapp" | "web"
    notification_opt_in: boolean

  # Service history
  history:
    previous_services:
      - service_type: string
        date: Date
        status: string
    open_tickets: string[]
    favorite_services: string[]

  # Accessibility
  accessibility:
    needs_simplified_language: boolean
    visual_impairment: boolean
    hearing_impairment: boolean
```

### 5.4 Conversation History Compression

For long conversations, use summarization:

```yaml
history_management:
  strategy: "sliding_window_with_summary"

  recent_turns:
    count: 8
    detail: "full"  # Keep complete messages

  older_turns:
    strategy: "summarize"
    summary_template: |
      "Previous conversation summary:
       - User asked about: [topics]
       - Information provided: [key points]
       - Actions taken: [completed actions]
       - Open items: [pending tasks]"

  context_injection_order:
    1. system_prompt
    2. user_profile (if authenticated)
    3. conversation_summary (if exists)
    4. recent_turns
    5. current_message
```

---

## 6. Escalation Patterns

### 6.1 Soft Escalation (Suggesting Human)

Offer without forcing:

```
# After second clarification failure
Bot: "Parece que podria ser mas facil explicar esto a un agente.

      Quieres que te conecte con una persona?
      [Si, conectar con agente] [No, prefiero seguir aqui]"

# Complex query detected
Bot: "Tu consulta involucra varios aspectos que un especialista
      podria explicarte mejor.

      Prefieres:
      [Continuar aqui] [Hablar con especialista]"
```

### 6.2 Hard Escalation (Forced Handoff)

For situations requiring human intervention:

```yaml
mandatory_escalation_triggers:
  keywords:
    - "emergencia"
    - "urgente"
    - "amenaza"
    - "peligro"
    - "denuncia penal"
    - "abuso"
    - "violencia"

  sentiment:
    - extreme_frustration (3+ negative signals)
    - anger_detected
    - distress_signals

  technical:
    - repeated_auth_failure
    - sensitive_data_request
    - legal_implications

  escalation_message: |
    "Esta situacion requiere atencion especializada.
     Te estoy conectando con un agente ahora.

     Tiempo de espera estimado: [tiempo]

     Mientras tanto:
     [Informacion de emergencia si aplica]"
```

### 6.3 Context Transfer Format

Structure for handoff to human agent:

```yaml
handoff_context:
  # Essential context
  summary:
    citizen_name: string
    citizen_contact: string
    channel: string

  # Conversation context
  conversation:
    initial_intent: string
    topics_discussed: string[]
    information_provided: string[]

  # Reason for escalation
  escalation:
    reason: string
    trigger: "user_request" | "system_detected" | "mandatory"
    sentiment: string

  # Collected information
  collected_data:
    slots_filled: object
    documents_uploaded: string[]

  # Full transcript
  transcript:
    turns: array
    total_duration: number

  # Recommendations
  agent_notes:
    suggested_response: string
    relevant_resources: string[]
    priority: "normal" | "high" | "urgent"
```

### 6.4 Re-engagement After Escalation

When human session ends:

```
Bot: "Gracias por contactarnos hoy, [nombre].

      Resumen de tu atencion:
      - Tema: [asunto]
      - Agente: [nombre_agente]
      - Resultado: [resolucion/siguiente_paso]

      Si necesitas algo mas, estoy aqui para ayudarte.
      [Nueva consulta] [Calificar atencion] [Cerrar]"
```

---

## 7. Proactive Patterns

### 7.1 Status Update Notifications

```yaml
proactive_notifications:
  ticket_update:
    trigger: "status_change"
    template: |
      "Hola [nombre], hay una actualizacion sobre tu tramite [folio]:

       Nuevo estado: [estado]
       Detalle: [descripcion]

       Necesitas hacer algo? [accion_requerida]

       [Ver detalles] [Tengo dudas]"

  appointment_reminder:
    trigger: "24h_before_appointment"
    template: |
      "Recordatorio: Tienes cita manana

       Fecha: [fecha]
       Hora: [hora]
       Lugar: [ubicacion]
       Tramite: [servicio]

       Documentos a llevar:
       - [documento_1]
       - [documento_2]

       [Confirmar asistencia] [Reagendar] [Cancelar]"
```

### 7.2 Deadline Reminders

```
Bot: "Hola [nombre], te recordamos:

      Tu [documento/tramite] vence en [X] dias ([fecha]).

      Para renovar a tiempo, necesitas:
      1. [Requisito 1]
      2. [Requisito 2]

      Quieres que te ayude a agendar la renovacion?
      [Agendar ahora] [Recordar despues] [Ya lo resolvi]"
```

### 7.3 Recommendation Triggers

```yaml
smart_recommendations:
  based_on_completed_service:
    - trigger: "license_renewal_completed"
      recommendation: |
        "Tip: Tu verificacion vehicular vence en [fecha].
         Quieres que te recuerde cuando sea momento de renovarla?"

  based_on_profile:
    - trigger: "student_profile_detected"
      recommendation: |
        "Sabias que hay becas disponibles para estudiantes?
         [Ver becas disponibles] [No me interesa]"

  based_on_location:
    - trigger: "new_address_registered"
      recommendation: |
        "Con tu nuevo domicilio, estos servicios te podrian interesar:
         - Cambio de domicilio en INE
         - Actualizacion de comprobante de domicilio

         [Ver mas] [No ahora]"
```

### 7.4 Follow-up Sequences

```
# After ticket creation
Day 0: "Tu queja [folio] ha sido registrada. Respuesta esperada: 5 dias."

Day 3: "Actualizacion: Tu queja [folio] esta siendo revisada por [dependencia]."

Day 5 (if no resolution):
      "Tu queja [folio] sigue en proceso.
       El equipo esta trabajando en ella.

       Quieres que escalemos tu caso?
       [Si, escalar] [Esperar mas] [Tengo nueva informacion]"

Day 7 (if resolved):
      "Tu queja [folio] ha sido resuelta:
       [Resumen de la resolucion]

       Esta solucion fue satisfactoria?
       [Si] [No, tengo dudas] [Reportar mismo problema]"
```

---

## 8. Government-Specific Patterns

### 8.1 Document Requirement Gathering

```
┌─────────────────────────────────────────────────────────────┐
│           DOCUMENT REQUIREMENT FLOW                          │
└─────────────────────────────────────────────────────────────┘

[User selects service]
    │
    ▼
[DISPLAY REQUIREMENTS]
    "Para [tramite], necesitas estos documentos:

     Obligatorios:
     □ INE o pasaporte vigente (original y copia)
     □ CURP (impresion reciente)
     □ Comprobante de domicilio (max 3 meses)

     Segun tu caso:
     □ [Documento condicional 1] - si aplica [condicion]
     □ [Documento condicional 2] - si aplica [condicion]

     Tienes todos los documentos?
     [Si, tengo todo] [Me falta algo] [No estoy seguro]"
    │
    ├── "Si, tengo todo"
    │       │
    │       ▼
    │   [Continue to scheduling/execution]
    │
    ├── "Me falta algo"
    │       │
    │       ▼
    │   [IDENTIFY MISSING]
    │       "Que documento te falta?
    │        □ INE - [Como obtenerlo]
    │        □ CURP - [Descarga gratuita aqui]
    │        □ Comprobante - [Opciones aceptadas]
    │        □ Otro"
    │       │
    │       ▼
    │   [PROVIDE HELP]
    │       "Para obtener [documento]:
    │        [Instrucciones paso a paso]
    │
    │        Cuando lo tengas, regresa y te ayudo
    │        a continuar con tu tramite.
    │        [Guardar mi progreso]"
    │
    └── "No estoy seguro"
            │
            ▼
        [CLARIFICATION DIALOG]
            "Dejame ayudarte a verificar.

             Tienes INE vigente (no vencida)?
             [Si] [No] [No se si esta vigente]"
            │
            ▼
        [Continue per response]
```

### 8.2 Eligibility Screening

```
┌─────────────────────────────────────────────────────────────┐
│              ELIGIBILITY SCREENING FLOW                      │
└─────────────────────────────────────────────────────────────┘

[User interested in benefit/program]
    │
    ▼
[EXPLAIN PROGRAM]
    "[Nombre del programa] proporciona [beneficio].

     Quieres verificar si calificas?
     [Si, verificar elegibilidad] [Solo quiero informacion]"
    │
    ├── Eligibility check requested
    │       │
    │       ▼
    │   [SCREENING QUESTIONS]
    │       "Voy a hacerte algunas preguntas rapidas.
    │
    │        1. Eres residente de Queretaro?
    │           [Si] [No]"
    │       │
    │       ▼
    │   [CONTINUE OR DISQUALIFY]
    │       │
    │       ├── Disqualified early
    │       │       │
    │       │       ▼
    │       │   "Lamentablemente, este programa es solo para
    │       │    residentes de Queretaro.
    │       │
    │       │    Alternativas para ti:
    │       │    - [Programa federal similar]
    │       │    - [Otro recurso]"
    │       │
    │       └── Continues
    │               │
    │               ▼
    │           [MORE QUESTIONS...]
    │               "2. Tu ingreso familiar mensual es:
    │                [Menos de $X] [$X a $Y] [Mas de $Y]"
    │       │
    │       ▼
    │   [FINAL DETERMINATION]
    │       │
    │       ├── Eligible
    │       │       "Buenas noticias! Pareces cumplir los requisitos.
    │       │
    │       │        Siguiente paso: [instrucciones]
    │       │        Documentos necesarios: [lista]
    │       │
    │       │        [Iniciar solicitud] [Ver mas detalles]"
    │       │
    │       ├── Possibly Eligible
    │       │       "Podrías ser elegible, pero necesitamos verificar
    │       │        algunos detalles mas.
    │       │
    │       │        Te recomiendo:
    │       │        [Hablar con asesor] [Revisar requisitos completos]"
    │       │
    │       └── Not Eligible
    │               "Basado en tus respuestas, no calificas para
    │                este programa porque: [razon]
    │
    │                Pero podrias calificar para:
    │                - [Programa alternativo 1]
    │                - [Programa alternativo 2]
    │
    │                [Explorar alternativas] [Hablar con asesor]"
```

### 8.3 Appointment Scheduling

```
┌─────────────────────────────────────────────────────────────┐
│              APPOINTMENT SCHEDULING FLOW                     │
└─────────────────────────────────────────────────────────────┘

[User requests appointment]
    │
    ▼
[GATHER SERVICE INFO]
    "Para que tramite necesitas cita?
     [Opcion 1] [Opcion 2] [Opcion 3] [Otro]"
    │
    ▼
[LOCATION SELECTION]
    "Selecciona la oficina mas conveniente:

     📍 Centro Civico - Disponibilidad: Alta
        Av. 5 de Febrero 35

     📍 Plaza de Armas - Disponibilidad: Media
        Madero 12, Centro

     📍 Modulo Plaza del Parque - Disponibilidad: Alta
        Blvd. Bernardo Quintana 300

     [Ver mapa de ubicaciones]"
    │
    ▼
[DATE SELECTION]
    "Fechas disponibles en [ubicacion]:

     Esta semana:
     [Mie 5] [Jue 6] [Vie 7]

     Proxima semana:
     [Lun 10] [Mar 11] [Mie 12] [Jue 13] [Vie 14]

     [Ver mas fechas]"
    │
    ▼
[TIME SELECTION]
    "Horarios disponibles para [fecha]:

     Manana:
     [9:00] [9:30] [10:00] [10:30] [11:00] [11:30]

     Tarde:
     [12:00] [12:30] [13:00] [14:00] [14:30] [15:00]"
    │
    ▼
[CONFIRM DETAILS]
    "Confirma tu cita:

     Tramite: [servicio]
     Fecha: [fecha completa]
     Hora: [hora]
     Lugar: [ubicacion + direccion]

     Documentos a llevar:
     ✓ [Documento 1]
     ✓ [Documento 2]

     [Confirmar cita] [Cambiar horario] [Cancelar]"
    │
    ▼
[CONFIRMATION]
    "Tu cita ha sido agendada!

     Numero de confirmacion: [codigo]

     Te enviare un recordatorio 24 horas antes.

     [Agregar a calendario] [Compartir detalles]
     [Modificar] [Cancelar cita]"
```

### 8.4 Status Checking Pattern

```yaml
status_check_flow:
  # With folio
  with_folio:
    prompt: "Dame tu numero de folio para buscar el estado de tu tramite."

    found:
      template: |
        "Estado de tu tramite {folio}:

         📋 Tipo: {tipo_tramite}
         📊 Estado: {estado_actual}
         📅 Ultima actualizacion: {fecha}

         {estado_detalle}

         Siguiente paso: {accion_requerida}
         Tiempo estimado: {tiempo_restante}"

      states:
        en_revision:
          icon: "🔄"
          message: "Tu solicitud esta siendo revisada por el area correspondiente."
          action: "Solo espera. Te notificaremos cuando haya novedades."

        requiere_documentos:
          icon: "📄"
          message: "Necesitamos documentacion adicional."
          action: "Adjunta los siguientes documentos: {lista_docs}"
          cta: "[Subir documentos]"

        aprobado:
          icon: "✅"
          message: "Tu tramite ha sido aprobado!"
          action: "Puedes pasar a recoger tu {documento} en {ubicacion}."
          cta: "[Ver horarios de atencion]"

        rechazado:
          icon: "❌"
          message: "Tu solicitud no fue aprobada."
          action: "Motivo: {razon}. Puedes apelar o reiniciar."
          cta: "[Iniciar apelacion] [Nueva solicitud]"

  # Without folio (search by identity)
  without_folio:
    requires_auth: true
    prompt: "No tienes el folio? Puedo buscar tus tramites activos con tu CURP."

    found_multiple:
      template: |
        "Encontre {count} tramites activos a tu nombre:

         1. {tramite_1.tipo} - {tramite_1.estado}
            Folio: {tramite_1.folio}

         2. {tramite_2.tipo} - {tramite_2.estado}
            Folio: {tramite_2.folio}

         Cual quieres revisar?
         [Ver primero] [Ver segundo] [Ver todos]"
```

---

## 9. Accessibility & Inclusive Design Patterns

### 9.1 Language Simplification

```yaml
simplified_language_mode:
  trigger: "accessibility_preference OR reading_level_detection"

  transformations:
    # Avoid jargon
    original: "Debes presentar tu constancia de situacion fiscal"
    simplified: "Necesitas un documento del SAT que dice cuanto ganas"

    # Shorter sentences
    original: "Para realizar este tramite, es necesario que primero
              acudas a la oficina correspondiente a obtener tu numero
              de folio, el cual deberas presentar junto con los
              documentos requeridos."
    simplified: "Primero: Ve a la oficina y pide un numero de folio.
                 Despues: Regresa con ese numero y tus documentos."

    # Active voice
    original: "La solicitud sera procesada en un plazo de 5 dias."
    simplified: "Revisamos tu solicitud en 5 dias."
```

### 9.2 Multilingual Support Pattern

```yaml
language_handling:
  detection:
    - explicit_selection
    - message_language_detection
    - user_profile_preference

  supported_languages:
    - es (Spanish - primary)
    - en (English)
    - otomi (indigenous - limited support)

  language_switch:
    prompt: |
      "I noticed you might prefer English.
       Would you like to continue in English?
       [Yes, English] [No, continuar en espanol]"

  indigenous_language:
    prompt: |
      "Detectamos que podrias preferir comunicarte en Otomi.
       Actualmente tenemos soporte limitado en Otomi.

       [Intentar en Otomi]
       [Continuar en espanol con interprete disponible]
       [Solicitar atencion presencial bilingue]"
```

---

## 10. Testing & Iteration Patterns

### 10.1 Conversation Test Scenarios

```yaml
test_scenarios:
  happy_path:
    - name: "Complete transaction flow"
      steps:
        - user: "Quiero renovar mi licencia"
        - expect: information_about_renewal
        - user: "Quiero agendar cita"
        - expect: location_options
        - user: selects_location
        - expect: date_options
        # ... complete flow

  edge_cases:
    - name: "Ambiguous query"
      steps:
        - user: "licencia"
        - expect: disambiguation_options

    - name: "Missing required info"
      steps:
        - user: "Quiero agendar cita"
        - expect: service_type_question
        - user: "no se"
        - expect: helpful_options_not_dead_end

    - name: "Invalid input recovery"
      steps:
        - user: provides_invalid_curp
        - expect: helpful_error_with_example
        - user: provides_valid_curp
        - expect: continues_flow

  escalation:
    - name: "Frustration detection"
      steps:
        - user: "Esto no funciona, estoy harto"
        - expect: empathy_and_escalation_offer

    - name: "Emergency keyword"
      steps:
        - user: "Esto es una emergencia"
        - expect: immediate_escalation
```

### 10.2 Key Metrics to Track

```yaml
conversation_metrics:
  success_metrics:
    - task_completion_rate: "% of intents successfully resolved"
    - first_contact_resolution: "% resolved without escalation"
    - average_turns_to_resolution: "fewer is better"

  failure_metrics:
    - fallback_rate: "% hitting error/unknown responses"
    - escalation_rate: "% requiring human handoff"
    - abandonment_rate: "% leaving mid-conversation"
    - loop_rate: "% entering repetitive clarification loops"

  quality_metrics:
    - clarification_efficiency: "% of clarifications that succeed"
    - slot_fill_accuracy: "% of extracted entities correct"
    - user_satisfaction_score: "post-conversation rating"

  alerts:
    - fallback_rate_threshold: "> 15% triggers review"
    - escalation_spike: "> 25% increase triggers investigation"
    - new_unhandled_intent: "flags for training data addition"
```

---

## 11. Implementation Checklist

### For Each Service Domain:

- [ ] Define happy path conversation flow
- [ ] Map all required slots and their validation rules
- [ ] Create disambiguation trees for ambiguous queries
- [ ] Write error messages for each failure type
- [ ] Design escalation triggers and handoff context
- [ ] Create proactive notification templates
- [ ] Test with edge cases and invalid inputs
- [ ] Review accessibility compliance
- [ ] Document API dependencies and failure handling
- [ ] Set up metrics tracking

### Cross-Domain:

- [ ] Standardize empathy phrase library
- [ ] Create shared disambiguation patterns
- [ ] Design universal error recovery flows
- [ ] Implement session state management
- [ ] Configure escalation routing rules
- [ ] Set up proactive notification system
- [ ] Test cross-domain transitions
- [ ] Validate multilingual support

---

## Sources

### Government Chatbot Design
- [Chatbots for Government in 2025: Examples, Use Cases, Statistics](https://botpress.com/blog/chatbots-for-government)
- [Chatbot Best Practices For Building Smart, Effective AI Bots - GovTech](https://insider.govtech.com/california/sponsored/chatbot-best-practices-for-building-smart-effective-ai-bots)
- [Government Chatbot Guide: Uses, Deployment, and Security](https://www.gptbots.ai/blog/government-chatbot)
- [24 Chatbot Best Practices You Can't Afford to Miss in 2025](https://botpress.com/blog/chatbot-best-practices)

### Multi-Turn Dialog Management
- [A Survey on Recent Advances in LLM-Based Multi-turn Dialogue Systems](https://dl.acm.org/doi/full/10.1145/3771090)
- [What Is Multi-Turn Conversation? A Guide for AI and Voice Systems](https://www.bland.ai/blogs/multi-turn-conversation)
- [Fine-Tuning LLMs for Multi-Turn Conversations](https://www.together.ai/blog/fine-tuning-llms-for-multi-turn-conversations-a-technical-deep-dive)
- [How To Build Multi-Turn AI Conversations With Rasa](https://rasa.com/blog/multi-turn-conversation)

### Disambiguation & Clarification
- [Chatbot UX Design: Complete Guide (2025)](https://www.parallelhq.com/blog/chatbot-ux-design)
- [Designing chatbots: how to design fallback logic](https://uxcontent.com/designing-chatbots-fallbacks/)
- [Chatbot Design Tips, Best Practices, and Examples for 2024](https://www.chatbot.com/blog/chatbot-design/)

### Error Recovery
- [Troubleshooting Conversations: Exploring Chatbot Repair Strategies](https://dl.acm.org/doi/10.1145/3670653.3677496)
- [Conversational Repair Strategies to Cope with Errors and Breakdowns](https://link.springer.com/chapter/10.1007/978-3-031-54975-5_2)
- [An analysis of dialogue repair in virtual assistants](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1356847/full)
- [Error Correction and Adaptation in Conversational AI](https://www.mdpi.com/2673-2688/5/2/41)

### Escalation Patterns
- [Chatbot to Human Handoff: Complete Guide to Transition (2025)](https://www.spurnow.com/en/blogs/chatbot-to-human-handoff)
- [When to hand off to a human: How to set effective AI escalation rules](https://www.replicant.com/blog/when-to-hand-off-to-a-human-how-to-set-effective-ai-escalation-rules)
- [Escalation Done Right: Best Practices for Handing Off from Chatbot to Human](https://cobbai.com/blog/chatbot-escalation-best-practices)
- [Chatbot handoff UX: How to design better transitions](https://standardbeagle.com/chatbot-handoff-ux/)

### Context Management
- [AI Chatbot Session Management: Best Practices](https://optiblack.com/insights/ai-chatbot-session-management-best-practices)
- [Context Engineering for Personalization - OpenAI Cookbook](https://cookbook.openai.com/examples/agents_sdk/context_personalization)
- [Efficient Context Management in LangChain Chatbots](https://www.dragonflydb.io/blog/efficient-context-management-in-langchain-with-dragonfly)
- [State management for advanced chatbots](https://rm-solutions.de/en/blog/show/state-management-bei-fortschrittlichen-chatbots/)

### Proactive AI
- [Towards Human-centered Proactive Conversational Agents](https://arxiv.org/html/2404.12670v1)
- [Proactive Conversational AI: A Comprehensive Survey](https://dl.acm.org/doi/10.1145/3715097)
- [Proactive Communication for CX: Use Cases and Benefits](https://www.mosaicx.com/blog/proactive-communication-use-cases)
- [PatternFly Conversation Design Guidelines](https://www.patternfly.org/patternfly-ai/conversation-design/)

### Slot Filling & Information Gathering
- [Implement slot-filling best practices - Microsoft Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/slot-filling-best-practices)
- [Slot Filling: A Comprehensive Guide for 2025](https://www.shadecoder.com/topics/slot-filling-a-comprehensive-guide-for-2025)
- [An Approach to Build Zero-Shot Slot-Filling System](https://arxiv.org/html/2406.08848v1)

### Appointment Scheduling
- [Appointment scheduling ChatBot - UX Research and UI Design](https://medium.com/design-bootcamp/appointment-scheduling-chatbot-ux-research-and-ui-design-f507661dc188)
- [How to Master the Art of AI Chatbot Conversation Flowcharts](https://sendbird.com/blog/ai-chatbot-conversation-flowcharts)
- [Appointment Scheduling Chatbot: Automate Your Bookings Fast](https://typebot.io/blog/appointment-scheduling-chatbot)

### Dialog Trees & Branching Logic
- [Chatbot Decision Tree: When to Implement, Benefits & Types](https://botpenguin.com/glossary/chatbot-decision-tree)
- [Game Writing Guide: How To Structure Branching Dialogue](https://indiegamewriting.com/writing-1-structuring-branching-dialogue/)

### Confirmation UX
- [Confirmation dialogs: How to design dialogs without irritation](https://uxplanet.org/confirmation-dialogs-how-to-design-dialogues-without-irritation-7b4cf2599956)
- [Your Ultimate Chatbot Best Practices Guide](https://www.chatbot.com/chatbot-best-practices/)

---

*Document prepared for: Gobierno de Queretaro AI Platform*
*Last updated: February 2026*
