# Payment Integration Patterns for Mexican Government AI

> Research document for Gobierno de Queretaro AI platform payment capabilities
> Last Updated: February 2026
> Domains: Agua CEA, Tramites Vehiculares, Cultura, Registro Publico, Vivienda IVEQ

---

## Executive Summary

This document provides comprehensive research on payment integration patterns for Mexican government chatbot services. The research covers payment gateways, CoDi/DiMo, SPEI, OXXO cash payments, card processing with PCI compliance, and WhatsApp Business payment capabilities. The findings support the implementation of in-chat payment capabilities across five government service domains in Queretaro.

### Key Findings

1. **OpenPay and Conekta dominate** the Mexican market (~99% of transactions), with strong government and enterprise support
2. **SPEI processed 5.34 billion transactions** in 2024, with 39% annual growth - the preferred method for larger payments
3. **OXXO Pay reaches unbanked populations** through 22,000+ stores with 7-day payment windows
4. **CoDi adoption remains low** (1.9M users) but DiMo is gaining traction (7M+ users in first year)
5. **PCI DSS v4.0.1** requirements became mandatory March 2025 - tokenization is essential for chatbots
6. **WhatsApp Business payments** in Mexico are limited to QR codes (Brazil/India only have full payments)

---

## 1. Payment Gateway Comparison

### Market Overview (2024-2025)

The Mexican payments market is projected to grow from $103 billion (2023) to $168 billion (2028) at a 10% CAGR. SPEI transactions increased 37% in 2024 with over 3.8 billion transactions processed.

| Gateway | Government Support | WhatsApp Compatible | Fees | Key Features |
|---------|-------------------|---------------------|------|--------------|
| **OpenPay (BBVA)** | Excellent - Banking integration | API-based (manual) | 2.9% + $0.30 USD | PCI DSS certified, fraud protection, card tokenization, BBVA Points support |
| **Conekta** | Good - Enterprise focus | API-based (manual) | 2.9% + $0.30 USD | 10+ years fraud engine, high-value transactions, PCI DSS, tokenization |
| **Stripe Mexico** | Limited | Payment Links | ~2.9% + variable | 3D Secure 2, global features, automatic reconciliation |
| **MercadoPago** | Good - LATAM coverage | Limited | Variable (negotiable) | QR codes, installments, Mercado Credits BNPL |
| **STP** | Excellent - Direct SPEI | API-based | Lower than cards | CLABE generation, real-time reconciliation, ISO 27001 certified |

### Recommended Gateways by Domain

| Domain | Primary Gateway | Secondary | Rationale |
|--------|----------------|-----------|-----------|
| **Agua CEA** | OpenPay + STP | Conekta | SPEI/CoDi for recurring, cards for immediate |
| **Tramites Vehiculares** | Conekta | OpenPay | High-value transactions, fraud protection |
| **Cultura** | Stripe/Conekta | MercadoPago | Event tickets need installments, international cards |
| **Registro Publico** | OpenPay | STP | Certificate fees vary, need receipt generation |
| **Vivienda IVEQ** | STP + Conekta | OpenPay | Housing payments benefit from SPEI direct deposit |

---

## 2. CoDi Integration

### How CoDi Works

CoDi (Cobro Digital) is Banxico's QR code-based payment system launched in 2019, operating on the SPEI infrastructure for real-time, zero-cost transactions.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Merchant   │────▸│   Banxico   │────▸│  User Bank  │
│  QR Code    │     │   CoDi API  │     │    App      │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │  1. Generate QR   │                   │
       │◂──────────────────│                   │
       │                   │  2. Scan & Auth   │
       │                   │◂──────────────────│
       │  3. Confirmation  │                   │
       │◂──────────────────│──────────────────▸│
```

### QR Code Generation in Chat

```javascript
// Example: Generate CoDi QR via STP API
const codiPayment = {
  amount: 1500.00,
  currency: "MXN",
  concept: "Pago Agua CEA - Cuenta 12345",
  reference: "CEA-2026-00001",
  expiration: "2026-02-07T23:59:59-06:00"
};

// Response includes QR code data for WhatsApp image message
const qrResponse = await stp.codi.generateQR(codiPayment);
// Returns: { qr_image_base64, codi_reference, expiration }
```

### Confirmation Webhooks

```javascript
// CoDi payment confirmation webhook
app.post('/webhooks/codi', (req, res) => {
  const { reference, status, timestamp, amount } = req.body;

  if (status === 'LIQUIDADO') {
    // Payment confirmed
    await updatePaymentStatus(reference, 'completed');
    await sendWhatsAppConfirmation(reference);
  }

  res.status(200).send('OK');
});
```

### Government Adoption Status

- **Current adoption**: 1.9 million active users, 9.4 million total transactions in 4 years
- **Challenges**: Low consumer awareness, limited bank app support
- **DiMo alternative**: Dinero Movil (launched March 2023) reached 7 million users in first year using phone number-based transfers

### Recommendation for Queretaro

Use CoDi/DiMo as a **secondary option** for tech-savvy users. Primary focus should be on SPEI and card payments given low CoDi adoption.

---

## 3. SPEI Integration

### Overview

SPEI (Sistema de Pagos Electronicos Interbancarios) processed **5.34 billion transactions** totaling MX$219 trillion in 2024 - equivalent to 6.5x Mexico's GDP. Adoption grew from 8.2% to 23.7% of Mexicans between 2021-2024.

### Reference Number Generation (CLABE)

The CLABE (Clave Bancaria Estandarizada) is an 18-digit standardized bank account identifier:

```
┌───────────┬───────────┬────────────────┬─────────┐
│ Bank Code │ Branch    │ Account Number │ Control │
│ (3 digits)│ (3 digits)│  (11 digits)   │(1 digit)│
└───────────┴───────────┴────────────────┴─────────┘

Example: 002 180 01234567890 1
         ─── ─── ─────────── ─
         BBVA Branch Account  Check
```

### Bank Integration Patterns

**Option A: STP Direct Integration**

```javascript
// Generate unique CLABE per user/transaction
const clabeAccount = await stp.accounts.create({
  alias: `CEA-${userId}`,
  type: 'collection',
  webhook_url: 'https://api.queretaro.gob.mx/webhooks/spei'
});

// Returns persistent CLABE for user
// e.g., 646180157000001234
```

**Option B: Payment Gateway Integration (Conekta/OpenPay)**

```javascript
// Via Conekta
const order = await conekta.Order.create({
  currency: 'MXN',
  customer_info: { customer_id: 'cus_abc123' },
  line_items: [{
    name: 'Pago Tenencia 2026',
    unit_price: 350000, // centavos
    quantity: 1
  }],
  charges: [{
    payment_method: {
      type: 'spei'
    }
  }]
});
// Response includes CLABE and reference for payment
```

### Reconciliation Approaches

| Approach | Pros | Cons |
|----------|------|------|
| **Unique CLABE per user** | Instant identification | More accounts to manage |
| **Single CLABE + reference** | Simple setup | Manual reconciliation possible |
| **Webhook-based** | Real-time updates | Requires reliable infrastructure |

### Timeout Handling

```javascript
// SPEI payment timeout handler
const SPEI_TIMEOUT_HOURS = 72; // Typical bank processing window

async function checkPendingSpeiPayments() {
  const pendingPayments = await Payment.findAll({
    where: {
      method: 'spei',
      status: 'pending',
      created_at: { [Op.lt]: moment().subtract(SPEI_TIMEOUT_HOURS, 'hours') }
    }
  });

  for (const payment of pendingPayments) {
    // Mark as expired, notify user
    await payment.update({ status: 'expired' });
    await sendWhatsAppMessage(payment.phone, templates.speiExpired);
  }
}
```

### Regulatory Updates (2024-2025)

- Enhanced cryptographic standards with increased key sizes
- Integration rules strengthened for fintech companies
- SPEI 2.0 roadmap announced with CBDC pilot planned for 2025-2026

---

## 4. OXXO/Cash Payments

### Overview

OXXO Pay enables cash payments at 22,000+ convenience stores, critical for reaching Mexico's unbanked population. Cash-based payments reached $6.1 billion in 2024.

### Barcode Generation

**Specifications:**
- Barcode Type: Code 128 (Variants C and D) or Interleaved 2 of 5
- Size: 1cm x 4cm to 6cm
- Alternative: 14-digit numeric reference code (no barcode needed)

```javascript
// Via Conekta
const oxxoCharge = await conekta.Order.create({
  currency: 'MXN',
  customer_info: {
    name: 'Juan Perez',
    email: 'juan@example.com',
    phone: '+524421234567'
  },
  line_items: [{
    name: 'Certificado Registro Publico',
    unit_price: 85000, // 850 MXN in centavos
    quantity: 1
  }],
  charges: [{
    payment_method: {
      type: 'oxxo_cash',
      expires_at: Math.floor(Date.now()/1000) + (7 * 24 * 60 * 60) // 7 days
    }
  }]
});

// Response includes:
// - oxxo_reference: 14-digit code
// - barcode_url: Image URL for voucher
// - expires_at: Unix timestamp
```

### Payment Verification Polling

OXXO payments are asynchronous. Verification options:

```javascript
// Option 1: Webhook (preferred)
app.post('/webhooks/conekta', (req, res) => {
  const event = req.body;

  if (event.type === 'charge.paid') {
    const reference = event.data.object.payment_method.reference;
    await processOxxoPayment(reference);
  }

  res.status(200).json({ received: true });
});

// Option 2: Polling (backup)
async function pollOxxoPayment(orderId, maxAttempts = 168) { // 7 days hourly
  for (let i = 0; i < maxAttempts; i++) {
    const order = await conekta.Order.find(orderId);
    if (order.payment_status === 'paid') {
      return order;
    }
    await sleep(3600000); // 1 hour
  }
  return null; // Expired
}
```

### Expiration Handling

```
Payment Window: 7 days (configurable, max 30 days)

Day 1: Generate voucher, send to user
Day 5: Reminder notification
Day 6: Final reminder
Day 7: Expiration, new voucher required
```

### User Communication Patterns

```javascript
const oxxoMessages = {
  voucher_generated: `
Tu ficha de pago OXXO esta lista:

Referencia: {{reference}}
Monto: ${{amount}} MXN
Vence: {{expiration_date}}

Presenta este codigo en cualquier OXXO.
Te notificaremos cuando recibamos tu pago.
  `,

  reminder: `
Recordatorio: Tu pago de {{service}} vence en {{days_remaining}} dias.

Referencia OXXO: {{reference}}
Monto: ${{amount}} MXN
  `,

  payment_confirmed: `
Pago recibido!

Servicio: {{service}}
Monto: ${{amount}} MXN
Folio: {{folio}}

Gracias por tu pago.
  `
};
```

---

## 5. Card Payments in Chat

### PCI DSS v4.0.1 Compliance Requirements (Mandatory March 2025)

**Key Requirements for Chatbot Payments:**

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| **Tokenization** | Replace card data with non-reversible tokens | Use gateway tokenization (never store PANs) |
| **Encryption** | TLS 1.3+ in transit, AES-256 at rest | All API calls over HTTPS |
| **CVV Handling** | Never store, audio redaction required | Real-time redaction in voice AI |
| **3D Secure** | Mandatory for online transactions | Gateway handles authentication flow |
| **Access Controls** | RBAC, least privilege | Audit all payment data access |
| **Testing** | Quarterly pen tests, vulnerability scans | Include chatbot APIs in scope |

### Tokenization Approaches

**Gateway Tokenization (Recommended)**

```javascript
// Client-side tokenization via OpenPay.js
// Card data never touches your servers

// Step 1: Generate token on client
const token = await OpenPay.token.create({
  card_number: "4111111111111111",
  holder_name: "Juan Perez",
  expiration_year: "26",
  expiration_month: "12",
  cvv2: "123"
});
// Returns: tok_xxx (token, not card data)

// Step 2: Use token server-side
const charge = await openpay.charges.create(customerId, {
  source_id: token.id, // Use token, never raw card
  amount: 1500.00,
  description: "Pago Tenencia Vehicular"
});
```

### 3D Secure Flows in WhatsApp

3D Secure requires browser redirection, which creates UX challenges in WhatsApp:

```
┌─────────────────────────────────────────────────────────────────┐
│                    3DS Flow for WhatsApp                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User provides payment info via secure link                  │
│     └─▸ WhatsApp → Payment Link (hosted page)                   │
│                                                                 │
│  2. Payment gateway initiates 3DS                               │
│     └─▸ Redirect to bank authentication                         │
│                                                                 │
│  3. User completes 3DS in browser                               │
│     └─▸ OTP/Biometric verification                              │
│                                                                 │
│  4. Return to success page                                      │
│     └─▸ Page triggers WhatsApp deep link or webhook             │
│                                                                 │
│  5. Confirmation in WhatsApp                                    │
│     └─▸ Chatbot sends receipt                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```javascript
// Generate secure payment link
const paymentLink = await createSecurePaymentLink({
  amount: 3500.00,
  service: 'tenencia_vehicular',
  userId: user.id,
  returnUrl: 'https://wa.me/524421234567?text=pago_completado'
});

// Send via WhatsApp
await sendWhatsAppMessage(user.phone, {
  type: 'interactive',
  interactive: {
    type: 'cta_url',
    body: { text: 'Completa tu pago de forma segura:' },
    action: {
      name: 'cta_url',
      parameters: {
        display_text: 'Pagar $3,500 MXN',
        url: paymentLink
      }
    }
  }
});
```

### Error Handling

```javascript
const cardErrorMessages = {
  'insufficient_funds': 'Tu tarjeta no tiene fondos suficientes.',
  'card_declined': 'Tu tarjeta fue rechazada. Intenta con otra.',
  'expired_card': 'Tu tarjeta esta vencida.',
  '3ds_failed': 'La verificacion de seguridad fallo. Intenta de nuevo.',
  'fraud_suspected': 'Por seguridad, tu pago requiere verificacion adicional.',
  'network_error': 'Error de conexion. Intenta en unos minutos.'
};
```

---

## 6. WhatsApp Business Payments

### Current Capabilities (2026)

| Feature | Mexico Status | Notes |
|---------|--------------|-------|
| **QR Code Payments** | Not Available | Only India and Brazil (Sept 2025) |
| **In-Chat Payments** | Not Available | No announced timeline for Mexico |
| **Payment Links** | Available | External redirect to payment page |
| **Interactive Buttons** | Available | CTA buttons to payment URLs |
| **Catalogs** | Available | Product listings without native checkout |

### Pricing Updates (2025-2026)

- **July 2025**: Message-based pricing model (replaces conversation-based)
- **October 2025**: Marketing rates reduced for Mexico
- **January 2026**: MXN billing available for approved businesses
- **April 2026**: MXN billing available for all businesses

### Limitations

1. **No native payment processing** - Must redirect to external payment pages
2. **3D Secure complications** - Requires browser for authentication
3. **Session limitations** - 24-hour window for service messages
4. **Template requirements** - Marketing messages need pre-approval

### Integration Patterns

**Pattern 1: Payment Link in Message**

```javascript
// Simple payment link
const message = {
  messaging_product: "whatsapp",
  to: phoneNumber,
  type: "interactive",
  interactive: {
    type: "cta_url",
    body: {
      text: "Tu pago de agua esta listo:\n\nMonto: $450.00 MXN\nConcepto: Agua CEA Enero 2026"
    },
    action: {
      name: "cta_url",
      parameters: {
        display_text: "Pagar ahora",
        url: paymentLink
      }
    }
  }
};
```

**Pattern 2: Payment Options Menu**

```javascript
// Offer multiple payment methods
const paymentOptions = {
  messaging_product: "whatsapp",
  to: phoneNumber,
  type: "interactive",
  interactive: {
    type: "list",
    body: { text: "Selecciona tu metodo de pago:" },
    action: {
      button: "Ver opciones",
      sections: [{
        title: "Metodos de pago",
        rows: [
          { id: "card", title: "Tarjeta de credito/debito" },
          { id: "spei", title: "Transferencia SPEI" },
          { id: "oxxo", title: "Pago en OXXO" },
          { id: "codi", title: "CoDi (QR)" }
        ]
      }]
    }
  }
};
```

### Future Outlook

- WhatsApp Business API projected to grow 20.7% annually through 2033
- In-chat shopping features expected (carts, restock notifications)
- Stablecoin and cross-border payment exploration by Meta
- No confirmed timeline for native payment processing in Mexico

---

## 7. Recommended Architecture

### Payment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Government Payment Architecture                   │
└─────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │    WhatsApp     │
                         │   Business API  │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │   AI Chatbot    │
                         │    (MARIA)      │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼─────────┐ ┌──────▼──────┐ ┌─────────▼─────────┐
    │  Payment Service  │ │  Backend    │ │  Notification     │
    │    Orchestrator   │ │  Systems    │ │  Service          │
    └─────────┬─────────┘ └─────────────┘ └───────────────────┘
              │
    ┌─────────┴─────────────────────────────────────┐
    │                                               │
┌───▼───┐  ┌────────┐  ┌───────┐  ┌──────┐  ┌─────▼────┐
│ STP   │  │OpenPay │  │Conekta│  │Stripe│  │MercadoPago│
│(SPEI) │  │(Cards) │  │(OXXO) │  │(Intl)│  │  (QR)    │
└───────┘  └────────┘  └───────┘  └──────┘  └──────────┘
```

### Service Architecture

```javascript
// Payment Orchestrator Service
class PaymentOrchestrator {

  async processPayment(request) {
    const { method, amount, service, userId, metadata } = request;

    // 1. Validate request
    await this.validatePaymentRequest(request);

    // 2. Create payment record
    const payment = await Payment.create({
      id: generatePaymentId(),
      userId,
      service,
      amount,
      method,
      status: 'pending',
      metadata
    });

    // 3. Route to appropriate gateway
    const gateway = this.getGateway(method);
    const gatewayResponse = await gateway.createPayment(payment);

    // 4. Return payment instructions
    return this.formatResponse(method, gatewayResponse);
  }

  getGateway(method) {
    const gateways = {
      'card': new OpenPayGateway(),
      'spei': new STPGateway(),
      'oxxo': new ConektaGateway(),
      'codi': new STPGateway(),
      'mercadopago': new MercadoPagoGateway()
    };
    return gateways[method];
  }
}
```

### Webhook Handling

```javascript
// Unified Webhook Handler
class WebhookHandler {

  async handleWebhook(source, payload, signature) {
    // 1. Verify signature
    if (!this.verifySignature(source, payload, signature)) {
      throw new UnauthorizedError('Invalid webhook signature');
    }

    // 2. Parse event
    const event = this.parseEvent(source, payload);

    // 3. Process based on event type
    switch (event.type) {
      case 'payment.completed':
        await this.handlePaymentCompleted(event);
        break;
      case 'payment.failed':
        await this.handlePaymentFailed(event);
        break;
      case 'payment.expired':
        await this.handlePaymentExpired(event);
        break;
    }

    // 4. Log for audit
    await AuditLog.create({
      source,
      eventType: event.type,
      paymentId: event.paymentId,
      timestamp: new Date()
    });

    return { received: true };
  }

  async handlePaymentCompleted(event) {
    const payment = await Payment.findById(event.paymentId);

    // Update payment status
    await payment.update({
      status: 'completed',
      completedAt: new Date(),
      gatewayReference: event.reference
    });

    // Update backend system (CEA, Vehicular, etc.)
    await this.updateBackendSystem(payment);

    // Generate receipt
    const receipt = await this.generateReceipt(payment);

    // Send WhatsApp confirmation
    await this.sendConfirmation(payment, receipt);
  }
}
```

### Receipt Generation

```javascript
// Receipt Generator
class ReceiptGenerator {

  async generate(payment) {
    const receipt = {
      folio: `QRO-${payment.service.toUpperCase()}-${Date.now()}`,
      date: new Date().toISOString(),
      service: this.getServiceName(payment.service),
      description: payment.metadata.description,
      amount: payment.amount,
      method: this.getMethodName(payment.method),
      reference: payment.gatewayReference,
      taxpayerInfo: await this.getTaxpayerInfo(payment.userId)
    };

    // Generate PDF
    const pdf = await this.generatePDF(receipt);

    // Store receipt
    await Receipt.create({
      paymentId: payment.id,
      folio: receipt.folio,
      pdfUrl: await this.uploadPDF(pdf)
    });

    return receipt;
  }

  getServiceName(service) {
    const names = {
      'agua_cea': 'Pago de Agua - CEA Queretaro',
      'tenencia': 'Tenencia Vehicular',
      'cultura_boleto': 'Boleto Evento Cultural',
      'registro_certificado': 'Certificado Registro Publico',
      'vivienda_iveq': 'Pago Vivienda IVEQ'
    };
    return names[service];
  }
}
```

### Refund Process

```javascript
// Refund Handler
class RefundHandler {

  async processRefund(paymentId, reason, requestedBy) {
    const payment = await Payment.findById(paymentId);

    // Validate refund eligibility
    if (!this.isRefundEligible(payment)) {
      throw new Error('Payment not eligible for refund');
    }

    // Create refund record
    const refund = await Refund.create({
      paymentId,
      amount: payment.amount,
      reason,
      requestedBy,
      status: 'pending'
    });

    // Process via gateway
    const gateway = this.getGateway(payment.method);
    const result = await gateway.refund(payment.gatewayReference, payment.amount);

    // Update statuses
    await refund.update({ status: 'completed', gatewayRefundId: result.id });
    await payment.update({ status: 'refunded' });

    // Notify user
    await this.notifyRefund(payment, refund);

    // Audit log
    await AuditLog.create({
      action: 'refund_processed',
      paymentId,
      refundId: refund.id,
      requestedBy,
      timestamp: new Date()
    });

    return refund;
  }
}
```

---

## 8. Security Requirements

### PCI DSS Compliance for Chatbots

**Scope Reduction Strategy:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PCI DSS Scope Management                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OUT OF SCOPE (via tokenization)                                │
│  ├── Chatbot application                                        │
│  ├── WhatsApp Business API                                      │
│  ├── Backend services                                           │
│  └── Database (stores tokens, not PANs)                         │
│                                                                 │
│  IN SCOPE                                                       │
│  ├── Payment gateway integration                                │
│  ├── Hosted payment pages                                       │
│  └── Webhook endpoints (receive payment confirmations)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Requirements:**

| PCI DSS Req | Description | Implementation |
|-------------|-------------|----------------|
| **3.4** | Render PAN unreadable | Gateway tokenization |
| **4.1** | Encrypt transmission | TLS 1.3 for all APIs |
| **6.5** | Address common vulnerabilities | Input validation, parameterized queries |
| **8.2** | Strong authentication | MFA for admin access |
| **10.1** | Audit trails | Log all payment-related actions |
| **11.2** | Vulnerability scanning | Quarterly scans, annual pen tests |
| **12.8** | Vendor management | Verify gateway PCI compliance |

### Data Handling

**What to Store:**

| Data | Store? | How |
|------|--------|-----|
| Payment tokens | Yes | Encrypted at rest |
| Transaction IDs | Yes | Plain text OK |
| Amounts | Yes | Encrypted or plain |
| Card numbers (PAN) | **NEVER** | Use tokenization |
| CVV/CVC | **NEVER** | Not even temporarily |
| 3DS data | **NEVER** | Gateway handles |
| User contact info | Yes | Encrypted, access controlled |

**Data Retention Policy:**

```javascript
const retentionPolicy = {
  paymentRecords: '7 years', // Tax/legal requirements
  auditLogs: '3 years',
  receipts: '7 years',
  tokens: 'Until user deletion or card expiry',
  webhookLogs: '90 days',
  errorLogs: '1 year'
};
```

### Audit Logging

```javascript
// Comprehensive Audit Log Schema
const AuditLog = {
  id: 'uuid',
  timestamp: 'datetime',
  action: 'string', // payment_initiated, payment_completed, refund_requested, etc.
  actor: {
    type: 'string', // user, system, admin
    id: 'string',
    ip: 'string'
  },
  resource: {
    type: 'string', // payment, refund, receipt
    id: 'string'
  },
  metadata: {
    amount: 'decimal',
    method: 'string',
    service: 'string',
    status: 'string'
  },
  result: 'string', // success, failure
  errorMessage: 'string?'
};

// Log all payment actions
async function logPaymentAction(action, payment, actor, result) {
  await AuditLog.create({
    id: uuid(),
    timestamp: new Date(),
    action,
    actor: {
      type: actor.type,
      id: actor.id,
      ip: actor.ip || 'N/A'
    },
    resource: {
      type: 'payment',
      id: payment.id
    },
    metadata: {
      amount: payment.amount,
      method: payment.method,
      service: payment.service,
      status: payment.status
    },
    result
  });
}
```

### Security Checklist

- [ ] All API communications use TLS 1.3+
- [ ] Card data tokenized via gateway SDK (client-side)
- [ ] Webhook signatures verified
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] RBAC for admin functions
- [ ] MFA for administrative access
- [ ] Quarterly vulnerability scans
- [ ] Annual penetration testing
- [ ] Incident response plan documented
- [ ] Third-party gateway PCI compliance verified
- [ ] Data retention policies enforced
- [ ] Audit logs tamper-protected

---

## 9. Queretaro-Specific Considerations

### Existing Infrastructure

Queretaro government already has digital payment infrastructure:

1. **APP QRO** - Official state application with:
   - Digital driver's license
   - Vehicle tax (Tenencia) payments
   - Water bill payments (CEA)
   - Insurance policy management

2. **CEA Queretaro** - Water utility with:
   - Online payments via ceaqueretaro.gob.mx
   - Mobile app
   - OXXO, Elektra, Soriana, Super Q payments

3. **Recaudanet** - Vehicle payment system:
   - 18-digit capture line
   - Call center support (442-211-7070)

### Integration Approach

The MARIA AI chatbot should integrate with existing systems rather than replace them:

```
┌─────────────────────────────────────────────────────────────────┐
│               Queretaro Payment Integration                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Request                                                   │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────────┐                                               │
│  │    MARIA     │                                               │
│  │   Chatbot    │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ├─────────┬─────────┬─────────┬─────────┐               │
│         ▼         ▼         ▼         ▼         ▼               │
│    ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐           │
│    │CEA API ││Recauda-││Cultura ││Registro││IVEQ   │           │
│    │        ││net API ││Portal  ││Publico ││Portal │           │
│    └────┬───┘└────┬───┘└────┬───┘└────┬───┘└────┬──┘           │
│         │         │         │         │         │               │
│         └─────────┴─────────┴─────────┴─────────┘               │
│                             │                                   │
│                    ┌────────▼────────┐                          │
│                    │ Payment Gateway │                          │
│                    │ (OpenPay/STP)   │                          │
│                    └─────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sources

### Payment Gateways
- [12 Best Payment Gateways in Mexico: Guide 2025 - Rebill](https://www.rebill.com/en/blog/payment-gateways-mexico)
- [Top 12 Payment Gateways in Mexico for 2025 - Mural](https://www.muralpay.com/blog/top-payment-gateways-in-mexico-fees-settlement-fx)
- [Payment Gateways in Mexico - Akurateco](https://akurateco.com/countries/mexico-payment-gateway)
- [Mexico Payment Gateways - Spreedly](https://www.spreedly.com/countries/mexico)

### CoDi and DiMo
- [From CoDi to DiMo: Mexico's Second Shot at Growing Digital Payments - Future Nexus](https://www.heyfuturenexus.com/codi-dimo-mexico-growing-digital-payments/)
- [Real-Time Digital Payments: The CoDi Case in Mexico - Mexico Business News](https://mexicobusiness.news/finance/news/real-time-digital-payments-codi-case-mexico)
- [Digital Payments CoDi - STP](https://stp.mx/en/digital-payments-codi/)
- [SPEI-CoDi: How Payments Work in Mexico - Finofo](https://www.finofo.com/blog/spei-codi-how-payments-work-in-mexico)

### SPEI Integration
- [SPEI - EBANX Docs](https://docs.ebanx.com/docs/payments/guides/accept-payments/api/mexico/spei/)
- [SPEI 2.0 and the Digital Peso - Mexico Business News](https://mexicobusiness.news/finance/news/spei-20-and-digital-peso-rethinking-instant-payments)
- [SPEI - Bamboo Payment Docs](https://docs.bamboopayment.com/en/docs/payment-methods/mexico/mx-apm-stp.html)
- [APIs - STP Mexico](https://stp.mx/en/apis/)

### OXXO Payments
- [OXXO Pay - EBANX Docs](https://docs.ebanx.com/docs/payments/guides/accept-payments/api/mexico/oxxo-pay/)
- [A Guide to OXXO Payments - Stripe](https://stripe.com/resources/more/oxxo-an-in-depth-guide)
- [OXXO Pay: A Guide to Mexico's Leading Payment Method - Nuvei](https://www.nuvei.com/posts/oxxo-pay)
- [OXXO - Worldpay](https://developer.worldpay.com/products/apms/oxxo)

### PCI DSS Compliance
- [PCI DSS Tokenization Guidelines - PCI Security Standards Council](https://www.pcisecuritystandards.org/documents/Tokenization_Guidelines_Info_Supplement.pdf)
- [Utilizing AI Chatbots for PCI DSS Compliance - Avahi](https://avahi.ai/blog/ai-chatbots-for-pci-dss-compliance/)
- [PCI DSS 4.0 Compliance Checklist for Voice AI - Hostie](https://hostie.ai/resources/pci-dss-4-0-compliance-checklist-voice-ai-card-payments-2025)
- [Preparing for PCI DSS 4.0 Compliance in 2025 - Thales](https://cpl.thalesgroup.com/blog/encryption/pci-dss-4-0-compliance-2025)

### WhatsApp Business
- [WhatsApp Business API Pricing 2026 - Flowcall](https://flowcall.co/blog/whatsapp-business-api-pricing-2026)
- [WhatsApp Payments - Infobip](https://www.infobip.com/blog/whatsapp-payments)
- [WhatsApp Business Platform Pricing](https://business.whatsapp.com/products/platform-pricing)
- [Future Improvements in WhatsApp API in 2026 - Zoko](https://www.zoko.io/post/whatsapp-api-future-business-communication)

### Gateway Documentation
- [Conekta Webhook Documentation](https://developers.conekta.com/docs/webhook)
- [OpenPay API Documentation](https://documents.openpay.mx/en/api)
- [Stripe 3D Secure Documentation](https://docs.stripe.com/payments/3d-secure)
- [MercadoPago Checkout API](https://www.mercadopago.com.mx/developers/en/docs/checkout-api-orders/integration-model)

### Chatbot Security
- [9 Chatbot Security Best Practices 2024 - Marketsy](https://marketsy.ai/blog/9-chatbot-security-best-practices-2024)
- [Chatbot Security Guide: Risks & Guardrails - Botpress](https://botpress.com/blog/chatbot-security)
- [Chatbot Security Essentials - Lakera](https://www.lakera.ai/blog/chatbot-security)

### Queretaro Government
- [APP QRO - Google Play](https://play.google.com/store/apps/details?id=appqro.queretaro.gob.mx)
- [Tenencia 2025 - Queretaro.gob.mx](https://www.queretaro.gob.mx/en/tenencia_2025)
- [CEA Queretaro Payment Options](https://aldialogo.mx/tramites-y-servicios/2025/11/03/donde-puedo-pagar-mi-recibo-de-agua-de-la-cea-en-queretaro)

---

## Appendix: Quick Reference

### Payment Method Selection Matrix

| Scenario | Recommended Method | Reason |
|----------|-------------------|--------|
| Immediate payment needed | Card | Instant confirmation |
| User prefers bank transfer | SPEI | Zero fees, trusted |
| User is unbanked | OXXO | Cash payment option |
| Small recurring payments | CoDi/DiMo | Zero cost, instant |
| High-value transaction | SPEI | Lower fees at scale |
| International card | Stripe | Better intl support |

### API Endpoints Quick Reference

```
OpenPay: https://api.openpay.mx/v1/{merchant_id}/
Conekta: https://api.conekta.io/
Stripe: https://api.stripe.com/v1/
MercadoPago: https://api.mercadopago.com/
STP: https://api.stp.mx/
```

### Webhook Event Types

| Gateway | Payment Success | Payment Failed | Refund |
|---------|----------------|----------------|--------|
| OpenPay | charge.succeeded | charge.failed | charge.refunded |
| Conekta | charge.paid | charge.declined | charge.refunded |
| Stripe | payment_intent.succeeded | payment_intent.payment_failed | charge.refunded |
| STP | payment.confirmed | payment.rejected | refund.completed |
