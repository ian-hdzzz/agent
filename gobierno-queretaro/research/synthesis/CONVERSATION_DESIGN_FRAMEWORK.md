# Conversation Design Framework

## Design Principles

### 1. Citizen-First Language
- Use everyday Spanish, not bureaucratic jargon
- Explain technical terms when necessary
- Match formality to context (casual for info, formal for legal)
- Support regional expressions used in Querétaro

### 2. Progressive Disclosure
- Start with simple options
- Provide more detail on request
- Don't overwhelm with information
- Guide step-by-step through complex processes

### 3. Empathetic Responses
- Acknowledge citizen concerns
- Validate frustrations appropriately
- Offer reassurance where genuine
- Maintain professional warmth

### 4. Action-Oriented
- Every conversation should lead to resolution or clear next step
- Minimize dead ends
- Always provide alternative paths
- Confirm understanding before proceeding

---

## Intent Taxonomy

### Universal Intents (All Domains)
```
info.general          - "¿Qué servicios ofrecen?"
info.hours            - "¿A qué hora abren?"
info.location         - "¿Dónde están ubicados?"
info.requirements     - "¿Qué documentos necesito?"
info.cost             - "¿Cuánto cuesta?"
info.timeline         - "¿Cuánto tarda?"

action.start_process  - "Quiero tramitar..."
action.check_status   - "¿Cómo va mi trámite?"
action.make_payment   - "Quiero pagar..."
action.schedule       - "Quiero hacer una cita"
action.cancel         - "Quiero cancelar..."
action.complain       - "Tengo una queja"

help.agent            - "Quiero hablar con alguien"
help.emergency        - "Es urgente"
help.other            - "Otra cosa"
```

### Domain-Specific Intents

#### Transport (AMEQ)
```
transport.card.balance    - "¿Cuánto saldo tengo?"
transport.card.history    - "Ver mis movimientos"
transport.card.new        - "Quiero tramitar tarjeta"
transport.card.renew      - "Renovar mi tarjeta"
transport.route.plan      - "¿Cómo llego a...?"
transport.route.map       - "Mapa de la ruta"
transport.report          - "Reportar problema"
```

#### Water (CEA)
```
water.bill.check          - "Ver mi recibo"
water.bill.explain        - "No entiendo mi recibo"
water.bill.pay            - "Pagar mi recibo"
water.meter.report        - "Reportar lectura"
water.leak.report         - "Reportar fuga"
water.service.new         - "Contratar servicio"
water.service.transfer    - "Cambio de nombre"
```

#### Vehicles
```
vehicle.tenencia.check    - "¿Cuánto debo de tenencia?"
vehicle.tenencia.pay      - "Pagar tenencia"
vehicle.receipt           - "Descargar comprobante"
vehicle.plates.replace    - "Reponer placas"
vehicle.office.find       - "Oficinas cercanas"
```

#### Education (USEBEQ)
```
education.enrollment.check    - "Ver preinscripción"
education.enrollment.status   - "Estado de mi registro"
education.school.info         - "Información de escuela"
education.requirements        - "Documentos para inscribir"
```

#### Crisis Services (Psychology, Women)
```
crisis.help.now           - "Necesito ayuda"
crisis.safety.check       - "No estoy segura"
crisis.info.resources     - "¿Qué servicios hay?"
crisis.appointment        - "Quiero una cita"
```

---

## Entity Recognition

### Common Entities
```yaml
entities:
  curp:
    pattern: "[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z]{2}"
    example: "GARS850101HQRRLN09"

  plate:
    pattern: "[A-Z]{3}-[0-9]{3}-[A-Z]|[A-Z]{3}-[0-9]{4}"
    example: "QRO-123-A"

  phone:
    pattern: "[0-9]{10}|[0-9]{3}-[0-9]{3}-[0-9]{4}"
    example: "4421234567"

  account_number:
    # Varies by service

  date:
    formats: ["DD/MM/YYYY", "D de mes", "mañana", "próximo lunes"]

  location:
    types: [address, neighborhood, landmark, coordinates]

  amount:
    pattern: "$[0-9,]+.?[0-9]*"
```

---

## Conversation Flows

### Standard Information Request Flow
```
User: [Question about service]
Bot: [Direct answer]
Bot: ¿Hay algo más en lo que te pueda ayudar?

Options:
- Sí, tengo otra pregunta
- No, gracias
- Quiero iniciar un trámite
```

### Service Initiation Flow
```
User: Quiero [service]
Bot: Claro, te ayudo con [service].
Bot: Para continuar, necesito algunos datos.
Bot: ¿Me puedes proporcionar tu CURP?

User: [CURP]
Bot: [Validate]
Bot: Gracias, [Name].
Bot: [Service-specific questions]
...
Bot: [Summary of collected information]
Bot: ¿Los datos son correctos?

User: Sí
Bot: [Process initiation]
Bot: Tu solicitud ha sido registrada con el folio [number].
Bot: Te notificaremos cuando haya actualizaciones.
```

### Payment Flow
```
User: Quiero pagar [service]
Bot: Te ayudo con el pago.
Bot: ¿Me proporcionas tu [identifier]?

User: [identifier]
Bot: [Lookup amount]
Bot: El monto a pagar es $[amount].
Bot: ¿Cómo deseas pagar?

Options:
- Tarjeta de crédito/débito
- Transferencia SPEI
- Pago en efectivo (OXXO)

User: [Selection]
Bot: [Generate payment reference/redirect]
Bot: [Confirmation instructions]
```

### Escalation Flow
```
[Trigger conditions met]
Bot: Veo que necesitas atención especializada.
Bot: Te voy a conectar con un asesor.
Bot: El tiempo de espera estimado es [time].

Options:
- Esperar
- Recibir llamada después
- Dejar mensaje

[If waiting]
Bot: Mientras esperas, ¿hay algo que pueda hacer por ti?
...
Bot: Un asesor está disponible. Te transfiero ahora.
[Handoff with context]
```

### Emergency Flow (Crisis Services)
```
[Emergency keywords detected]
Bot: Entiendo que esta es una situación difícil.
Bot: Tu seguridad es lo más importante.

[If immediate danger]
Bot: Si estás en peligro inmediato, llama al 911.
Bot: También puedes llamar a la línea de emergencia: [number]

[If not immediate]
Bot: Estoy aquí para ayudarte a encontrar apoyo.
Bot: Todo lo que compartas es confidencial.
[Continue with sensitive intake]
```

---

## Response Templates

### Greeting
```
Standard:
"¡Hola! Soy el asistente virtual del Gobierno de Querétaro.
¿En qué te puedo ayudar hoy?"

Returning user:
"¡Hola de nuevo, [Name]!
¿Quieres continuar con [previous topic] o necesitas algo diferente?"

After hours:
"¡Hola! Aunque es fuera de horario de oficina,
puedo ayudarte con información y algunos trámites.
Para atención personalizada, nuestro horario es [hours]."
```

### Confirmation
```
"Perfecto, he registrado tu solicitud."
"Tu número de folio es: [number]"
"Guarda este número para dar seguimiento."
```

### Apology/Error
```
"Lo siento, hubo un problema al procesar tu solicitud."
"Puedes intentar de nuevo o contactar a un asesor."
"Disculpa la molestia, estamos trabajando para resolverlo."
```

### Empathy (Crisis)
```
"Entiendo que esta situación es difícil."
"No estás sola/solo."
"Es muy valiente que busques ayuda."
"Tu bienestar es importante para nosotros."
```

### Closure
```
Standard:
"¿Hay algo más en lo que pueda ayudarte?"

After resolution:
"Me da gusto haberte ayudado. ¡Que tengas buen día!"

Survey prompt:
"¿Podrías calificar tu experiencia del 1 al 5?
Tu opinión nos ayuda a mejorar."
```

---

## Handling Edge Cases

### Unknown Intent
```
Bot: No estoy seguro de entender. ¿Podrías explicarlo de otra manera?

Options:
- Ver opciones disponibles
- Hablar con un asesor
- [Suggested intents based on keywords]
```

### Invalid Input
```
Bot: El [tipo de dato] que ingresaste no parece ser válido.
Bot: El formato correcto es [format].
Bot: ¿Podrías verificarlo e intentar de nuevo?
```

### System Unavailable
```
Bot: Lo siento, el sistema de [service] no está disponible en este momento.
Bot: Puedes intentar más tarde o contactar directamente al [phone].
Bot: ¿Te puedo ayudar con algo más mientras tanto?
```

### Out of Scope
```
Bot: Ese tema no corresponde a los servicios del Gobierno de Querétaro.
Bot: Te sugiero contactar a [appropriate entity].
Bot: ¿Hay algo más en lo que pueda ayudarte?
```

---

## Quality Assurance

### Response Quality Checklist
- [ ] Answer is accurate and current
- [ ] Language is clear and accessible
- [ ] Appropriate empathy/tone for context
- [ ] Clear next steps provided
- [ ] No dead ends
- [ ] Escalation path available

### Conversation Metrics
- Task completion rate
- Turns to resolution
- Escalation rate
- User satisfaction score
- Repeat contact rate
