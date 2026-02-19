# Integration Specifications

## Government Backend Systems Identified

### 1. AMEQ / IQT (Transport)
- **System**: QROBUS
- **Capabilities Needed**:
  - Card balance lookup
  - Transaction history
  - Card status check
  - Route information
- **API Requirements**:
  - `GET /cards/{card_number}/balance`
  - `GET /cards/{card_number}/history`
  - `GET /routes/search?from={location}&to={location}`
  - `GET /routes/{route_id}/map`

### 2. CEA (Water)
- **System**: Billing/CRM System
- **Capabilities Needed**:
  - Bill lookup by account
  - Payment status
  - Usage history
  - Leak report submission
  - Service request tracking
- **API Requirements**:
  - `GET /accounts/{account_id}/balance`
  - `GET /accounts/{account_id}/bills`
  - `POST /reports/leak`
  - `GET /cases/{case_id}/status`

### 3. USEBEQ (Education)
- **System**: SAID (Sistema de Asignación)
- **Capabilities Needed**:
  - CURP-based enrollment lookup
  - School assignment check
  - Vinculación status
  - Preinscription status
- **API Requirements**:
  - `GET /enrollment/{curp}/status`
  - `GET /enrollment/{curp}/assignment`
  - `GET /schools/{school_id}/info`

### 4. Secretaría de Finanzas (Vehicles)
- **System**: Portal Tributario
- **Capabilities Needed**:
  - Tenencia debt lookup
  - Payment generation
  - Receipt download
  - Vehicle registry lookup
- **API Requirements**:
  - `GET /vehicles/{plate}/debt`
  - `POST /vehicles/{plate}/payment`
  - `GET /vehicles/{plate}/receipt`

### 5. RPP (Property Registry)
- **System**: CERLIN / SIRE
- **Capabilities Needed**:
  - Property lookup (folio, catastral, location)
  - Certificate request status
  - Document generation
  - Alert registration
- **API Requirements**:
  - `GET /properties/search`
  - `GET /certificates/{id}/status`
  - `POST /alerts/register`

### 6. IVEQ (Housing)
- **System**: IVEQ Portal / Citas System
- **Capabilities Needed**:
  - No-debt certificate lookup
  - Appointment scheduling
  - Program eligibility check
  - Application status
- **API Requirements**:
  - `GET /properties/{id}/debt-status`
  - `POST /appointments`
  - `GET /programs/eligibility`

### 7. CCLQ (Labor)
- **System**: CENCOLAB
- **Capabilities Needed**:
  - Case submission
  - Case status tracking
  - Appointment scheduling
- **API Requirements**:
  - `POST /cases`
  - `GET /cases/{id}/status`
  - `POST /appointments`

### 8. SEDESOQ (Social Programs)
- **System**: Tarjeta Contigo
- **Capabilities Needed**:
  - Card balance
  - Benefit status
  - Program eligibility
  - Enrollment status
- **API Requirements**:
  - `GET /cards/{id}/balance`
  - `GET /beneficiaries/{curp}/status`
  - `GET /programs/eligibility`

---

## Shared Service Implementations

### Identity Service (CURP-Based)

```yaml
identity_service:
  endpoints:
    validate_curp:
      method: POST
      path: /identity/validate
      input:
        curp: string (18 chars)
      output:
        valid: boolean
        name: string
        dob: date
        gender: string
        state: string

    link_accounts:
      method: POST
      path: /identity/link
      input:
        curp: string
        service: enum [transport, water, vehicles, etc.]
        account_id: string
      output:
        linked: boolean

    get_profile:
      method: GET
      path: /identity/{curp}/profile
      output:
        linked_services: array
        contact_preferences: object
        language: string
```

### Payment Gateway

```yaml
payment_gateway:
  providers:
    - SPEI
    - Credit/Debit Cards
    - OXXO Pay (cash reference)
    - PayPal (optional)

  endpoints:
    create_payment:
      method: POST
      path: /payments
      input:
        amount: decimal
        service: string
        reference: string
        method: enum [card, spei, cash_reference]
        citizen_id: string
      output:
        payment_id: string
        reference_number: string
        expiry: datetime (for cash)
        redirect_url: string (for card)

    check_payment:
      method: GET
      path: /payments/{payment_id}
      output:
        status: enum [pending, completed, failed, expired]
        completion_date: datetime
        receipt_url: string

    generate_receipt:
      method: GET
      path: /payments/{payment_id}/receipt
      output:
        pdf_url: string
```

### Appointment System

```yaml
appointment_system:
  endpoints:
    get_availability:
      method: GET
      path: /appointments/availability
      input:
        service: string
        location: string
        date_from: date
        date_to: date
      output:
        slots: array of {date, time, available_count}

    create_appointment:
      method: POST
      path: /appointments
      input:
        service: string
        location: string
        slot: datetime
        citizen_curp: string
        purpose: string
      output:
        appointment_id: string
        confirmation_code: string
        qr_code: string

    reschedule:
      method: PUT
      path: /appointments/{id}
      input:
        new_slot: datetime
      output:
        success: boolean
        new_confirmation: string

    cancel:
      method: DELETE
      path: /appointments/{id}
```

### Notification Service

```yaml
notification_service:
  channels:
    - whatsapp
    - sms
    - email
    - push (mobile app)

  endpoints:
    send_notification:
      method: POST
      path: /notifications
      input:
        citizen_id: string
        channel: enum
        template: string
        variables: object
        schedule: datetime (optional)
      output:
        notification_id: string
        status: enum [queued, sent, delivered, failed]

    get_preferences:
      method: GET
      path: /notifications/preferences/{citizen_id}
      output:
        preferred_channel: enum
        opt_outs: array
        language: string

  templates:
    - appointment_reminder
    - payment_confirmation
    - payment_due
    - case_update
    - document_ready
    - emergency_alert
```

### Case Management / CRM

```yaml
case_management:
  endpoints:
    create_case:
      method: POST
      path: /cases
      input:
        citizen_curp: string
        service: string
        type: string
        description: string
        priority: enum [low, medium, high, urgent]
        channel: string
      output:
        case_id: string
        status: enum
        assigned_to: string

    update_case:
      method: PUT
      path: /cases/{id}
      input:
        status: enum
        notes: string
        resolution: string (if closing)

    get_case_history:
      method: GET
      path: /cases/citizen/{curp}
      output:
        cases: array

    escalate:
      method: POST
      path: /cases/{id}/escalate
      input:
        reason: string
        target_team: string
```

---

## Security Requirements

### Authentication
- API keys for service-to-service
- OAuth 2.0 for citizen-facing
- JWT tokens with short expiry
- Rate limiting per service

### Data Protection
- All PII encrypted at rest
- TLS 1.3 for transit
- Data masking in logs
- Audit trail for all access

### Compliance
- Mexican data protection law (LFPDPPP)
- Government data standards
- Retention policies by data type

---

## Error Handling Standards

```yaml
error_response:
  format:
    error_code: string
    message: string (user-friendly, Spanish)
    details: string (technical, for logging)
    retry_after: integer (seconds, if applicable)

  common_codes:
    AUTH_001: "Sesión expirada"
    AUTH_002: "Acceso no autorizado"
    VAL_001: "CURP inválido"
    VAL_002: "Datos incompletos"
    SYS_001: "Servicio temporalmente no disponible"
    SYS_002: "Error de conexión con sistema externo"
    PAY_001: "Pago rechazado"
    PAY_002: "Referencia de pago expirada"
```

---

## Monitoring & Observability

### Metrics to Track
- Response times per service
- Error rates per endpoint
- Transaction volumes
- User satisfaction scores
- Conversation completion rates

### Alerting Thresholds
- Response time > 3s: Warning
- Response time > 10s: Critical
- Error rate > 5%: Warning
- Error rate > 10%: Critical
- System unavailable: Immediate page

### Dashboards
- Real-time service health
- Daily transaction summary
- Weekly trend analysis
- Monthly executive report
