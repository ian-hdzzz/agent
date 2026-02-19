# Error Handling Framework for Government AI

## Executive Summary

This document provides a comprehensive error handling framework for the Gobierno de Queretaro AI chatbot platform (MARIA). The framework addresses error handling across all 13 service domains, ensuring graceful degradation, user-friendly messaging, and system resilience when integrating with multiple backend systems including CEA (water services), SAT (property tax), transit permits, and citizen services.

**Key Principles:**
- Errors are opportunities to maintain trust, not just technical failures
- Users should never encounter dead ends or technical jargon
- Every error path must lead to a resolution or escalation
- System resilience through retry, circuit breaker, and fallback patterns

---

## 1. Error Classification

### 1.1 Error Categories

| Category | Examples | User Impact | Recovery Strategy | Priority |
|----------|----------|-------------|-------------------|----------|
| **Transient** | API timeout, rate limit, network glitch | Brief delay | Auto-retry with exponential backoff | P1 |
| **Permanent** | Invalid CURP, record not found, invalid input format | Cannot proceed | Clear error message + alternatives | P2 |
| **System** | Service down, scheduled maintenance, database unavailable | Feature unavailable | Graceful degradation + fallback | P1 |
| **User Input** | Ambiguous request, invalid format, missing data | Clarification needed | Re-prompt with guidance + examples | P3 |
| **Authentication** | Session expired, invalid credentials, unauthorized access | Access denied | Re-authentication flow | P2 |
| **Business Logic** | Insufficient balance, duplicate request, deadline passed | Action rejected | Explanation + alternative options | P2 |

### 1.2 Error Severity Levels

| Level | Description | Response Time | Notification |
|-------|-------------|---------------|--------------|
| **Critical** | Complete service outage | Immediate | Alert team + automated escalation |
| **High** | Major feature unavailable | < 5 minutes | Alert team |
| **Medium** | Degraded performance | < 30 minutes | Log + monitor |
| **Low** | Minor issues, cosmetic | Next business day | Log only |

---

## 2. Retry and Backoff Patterns

### 2.1 Exponential Backoff Formula

```typescript
// Exponential backoff with jitter
function calculateBackoff(attempt: number, config: BackoffConfig): number {
  const baseDelay = config.baseDelayMs; // e.g., 1000ms
  const maxDelay = config.maxDelayMs;   // e.g., 30000ms
  const jitterFactor = config.jitter;   // e.g., 0.1-0.5

  // Exponential calculation: baseDelay * 2^attempt
  let delay = baseDelay * Math.pow(2, attempt);

  // Cap at maximum delay
  delay = Math.min(delay, maxDelay);

  // Add jitter to prevent thundering herd
  const jitter = delay * jitterFactor * Math.random();
  return delay + jitter;
}

// Example progression (base: 1s, max: 30s, jitter: 0.2):
// Attempt 1: ~1.0-1.2s
// Attempt 2: ~2.0-2.4s
// Attempt 3: ~4.0-4.8s
// Attempt 4: ~8.0-9.6s
// Attempt 5: ~16-19.2s
// Attempt 6+: ~30-36s (capped)
```

### 2.2 Retry Configuration by Service Type

| Service Type | Max Retries | Base Delay | Max Delay | Timeout |
|--------------|-------------|------------|-----------|---------|
| CEA SOAP API | 3 | 2000ms | 30000ms | 45s |
| REST APIs | 3 | 1000ms | 15000ms | 30s |
| Payment Gateways | 2 | 3000ms | 10000ms | 60s |
| Database Queries | 2 | 500ms | 5000ms | 15s |
| External Services | 3 | 1500ms | 20000ms | 30s |

### 2.3 Circuit Breaker Implementation

```typescript
interface CircuitBreakerConfig {
  failureThreshold: number;    // Failures before opening (e.g., 5)
  successThreshold: number;    // Successes to close (e.g., 3)
  timeout: number;             // Time in open state (e.g., 60000ms)
  halfOpenRequests: number;    // Requests allowed in half-open (e.g., 3)
}

enum CircuitState {
  CLOSED,    // Normal operation
  OPEN,      // Blocking requests
  HALF_OPEN  // Testing recovery
}

class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number = 0;

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.lastFailureTime > this.config.timeout) {
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      } else {
        throw new CircuitOpenError('Service temporarily unavailable');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.config.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.failureCount = 0;
      }
    } else {
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitState.OPEN;
    }
  }
}
```

### 2.4 Service-Specific Circuit Breaker Settings

| Service | Failure Threshold | Recovery Timeout | Half-Open Requests |
|---------|-------------------|------------------|-------------------|
| CEA Water API | 5 failures | 60 seconds | 3 |
| SAT Property Tax | 5 failures | 60 seconds | 3 |
| Payment Gateway | 3 failures | 120 seconds | 2 |
| Transit Permits | 5 failures | 45 seconds | 3 |
| External Validators | 4 failures | 90 seconds | 2 |

---

## 3. Graceful Degradation Strategies

### 3.1 Degradation Hierarchy

```
Level 0: Full Functionality
    ↓ (on failure)
Level 1: Cached Data Fallback
    ↓ (on failure)
Level 2: Reduced Functionality Mode
    ↓ (on failure)
Level 3: Queue for Later Processing
    ↓ (on failure)
Level 4: Human Escalation
```

### 3.2 Cached Data Fallbacks

| Service | Cacheable Data | Cache TTL | Fallback Action |
|---------|---------------|-----------|-----------------|
| CEA Water | Rate tables, service areas | 24 hours | Show cached rates with disclaimer |
| SAT Property | Tax rates, payment deadlines | 12 hours | Show general info + suggest retry |
| Transit | Fee schedules, requirements | 24 hours | Display requirements from cache |
| Procedures | Step-by-step guides | 48 hours | Show cached guide |

```typescript
async function getWithFallback<T>(
  primarySource: () => Promise<T>,
  cacheKey: string,
  fallbackValue?: T
): Promise<{ data: T; source: 'live' | 'cache' | 'fallback'; stale: boolean }> {
  try {
    const data = await primarySource();
    await cache.set(cacheKey, data, TTL);
    return { data, source: 'live', stale: false };
  } catch (error) {
    const cached = await cache.get<T>(cacheKey);
    if (cached) {
      const isStale = cached.timestamp < Date.now() - STALE_THRESHOLD;
      return { data: cached.value, source: 'cache', stale: isStale };
    }
    if (fallbackValue) {
      return { data: fallbackValue, source: 'fallback', stale: true };
    }
    throw error;
  }
}
```

### 3.3 Reduced Functionality Modes

| Normal Mode | Degraded Mode | Trigger |
|-------------|---------------|---------|
| Real-time balance lookup | Estimated balance + last known reading | CEA API down |
| Online payment processing | Queue payment + send confirmation later | Payment gateway down |
| Instant permit validation | Accept request + validate async | Transit API down |
| Live appointment scheduling | Collect info + callback queue | Scheduling system down |

### 3.4 Queue for Later Processing

```typescript
interface DeferredRequest {
  id: string;
  type: 'payment' | 'permit' | 'appointment' | 'complaint';
  payload: any;
  userId: string;
  contactInfo: {
    phone?: string;
    email?: string;
    chatwootId?: string;
  };
  createdAt: Date;
  retryCount: number;
  maxRetries: number;
  priority: 'high' | 'medium' | 'low';
}

// User-facing message when queueing
const queueMessage = {
  es: `Hemos registrado tu solicitud con el folio #{id}.
       Te notificaremos por {channel} cuando se procese.
       Tiempo estimado: {estimatedTime}.`
};
```

### 3.5 Human Escalation Triggers

| Condition | Escalation Type | Response |
|-----------|-----------------|----------|
| 3+ consecutive failures | Automatic | Transfer to agent queue |
| Sentiment detection: frustrated | Proactive | Offer human assistance |
| High-value transaction failure | Immediate | Priority queue |
| Sensitive data involved | Policy-based | Require human verification |
| User explicit request | On-demand | Immediate transfer |

---

## 4. User-Facing Error Messages

### 4.1 Message Templates (Spanish)

#### Transient Errors
```
# API Timeout
"Estamos verificando tu informacion. Un momento por favor..."
[Show loading indicator for 5-10 seconds before next message]

# Rate Limited
"Tenemos muchas solicitudes en este momento.
En unos segundos continuamos con tu consulta."

# Network Issue
"Estamos restableciendo la conexion con el sistema.
Esto tomara solo unos segundos."

# Retry in Progress
"Seguimos trabajando en tu solicitud. Gracias por tu paciencia."
```

#### Not Found Errors
```
# Record Not Found - CURP
"No encontramos registros con la CURP {curp}.
Por favor verifica que:
- Los datos esten escritos correctamente
- No haya espacios adicionales
Puedes intentar de nuevo o consultar con otro dato."

# Account Not Found
"No localizamos una cuenta con ese numero.
Verifica el numero en tu recibo de agua (10 digitos)
o proporciona tu direccion completa."

# No Pending Payments
"Excelente noticia: no tienes adeudos pendientes
con el numero de cuenta {account}."
```

#### System Unavailable
```
# Scheduled Maintenance
"El sistema de {service} esta en mantenimiento programado.
Estara disponible nuevamente a las {time}.
Mientras tanto, puedo ayudarte con otras consultas."

# Unexpected Outage
"El servicio de {service} no esta disponible temporalmente.
Opciones disponibles:
1. Intentar nuevamente en unos minutos
2. Dejarte un recordatorio para despues
3. Conectarte con un agente
Que prefieres?"

# Partial System Failure
"Puedo mostrarte informacion general, pero algunos datos
en tiempo real no estan disponibles. Los datos mostrados
fueron actualizados el {date}."
```

#### Invalid Input
```
# Invalid Format - General
"El formato no es correcto. Por ejemplo, para {field}:
Formato correcto: {example}
Por favor ingresa nuevamente."

# Invalid CURP Format
"La CURP debe tener 18 caracteres alfanumericos.
Ejemplo: GARC850101HDFRRL09
Verifica y vuelve a ingresarla."

# Invalid Phone
"Necesito un numero de telefono de 10 digitos.
Ejemplo: 4421234567
Cual es tu numero?"

# Invalid Email
"El correo electronico no parece valido.
Ejemplo: nombre@ejemplo.com
Puedes verificarlo?"
```

#### Payment Errors
```
# Insufficient Funds
"El pago no pudo procesarse. Verifica que tu tarjeta
tenga fondos suficientes e intenta nuevamente."

# Card Declined
"Tu tarjeta fue rechazada por el banco.
Puedes:
1. Intentar con otra tarjeta
2. Verificar con tu banco
3. Pagar en oficinas CEA"

# Payment Timeout
"La conexion con el banco tomo mas tiempo del esperado.
NO se realizo ningun cargo a tu tarjeta.
Deseas intentar nuevamente?"

# Duplicate Payment
"Ya existe un pago registrado con estos datos del dia {date}.
Si crees que es un error, puedo conectarte con un agente
para verificar."
```

#### Authentication Errors
```
# Session Expired
"Tu sesion ha expirado por seguridad.
Por favor, proporciona nuevamente tu numero de cuenta
para continuar."

# Unauthorized Access
"Necesito verificar tu identidad para acceder a esta informacion.
Por favor proporciona tu numero de cuenta y CURP."
```

### 4.2 Message Design Principles

1. **Never expose technical details**
   - Bad: "Error 500: Internal Server Error - Database connection timeout"
   - Good: "Estamos experimentando dificultades tecnicas. Intentemos de nuevo."

2. **Always provide next steps**
   - Bad: "No se encontro la cuenta."
   - Good: "No encontramos esa cuenta. Verifica el numero o proporciona tu direccion."

3. **Maintain conversational tone**
   - Bad: "CURP invalida. Reingrese dato."
   - Good: "Esa CURP no parece correcta. Debe tener 18 caracteres, por ejemplo: GARC850101HDFRRL09"

4. **Offer alternatives**
   - Bad: "Sistema no disponible."
   - Good: "Este servicio no esta disponible ahora. Puedo ayudarte con otra consulta o conectarte con un agente."

5. **Use progressive disclosure**
   - First failure: "Un momento, estamos verificando..."
   - Second failure: "Sigue tomando un poco mas de tiempo..."
   - Third failure: "Parece que hay un problema. Te ofrezco estas opciones..."

6. **Acknowledge and empathize**
   - "Entiendo que esto puede ser frustrante. Dejame ayudarte..."
   - "Lamento la demora. Esto no es lo habitual..."

---

## 5. API-Specific Error Handling

### 5.1 SOAP APIs (CEA Water Services)

#### Timeout Handling
```typescript
const CEA_SOAP_CONFIG = {
  connectionTimeout: 30000,    // 30 seconds to establish connection
  socketTimeout: 45000,        // 45 seconds for response
  retries: 3,
  backoffBase: 2000,
};

async function callCEASoapService(operation: string, params: any) {
  const client = await createSoapClient(CEA_WSDL_URL, {
    connection_timeout: CEA_SOAP_CONFIG.connectionTimeout,
    request_timeout: CEA_SOAP_CONFIG.socketTimeout,
  });

  return withRetry(
    () => client[operation](params),
    {
      maxRetries: CEA_SOAP_CONFIG.retries,
      baseDelay: CEA_SOAP_CONFIG.backoffBase,
      shouldRetry: (error) => isTransientSoapError(error),
    }
  );
}
```

#### XML Parsing Errors
```typescript
function handleSoapError(error: any): UserFacingError {
  // SOAP Fault parsing
  if (error.root?.Envelope?.Body?.Fault) {
    const fault = error.root.Envelope.Body.Fault;
    const faultCode = fault.faultcode || fault.Code?.Value;
    const faultString = fault.faultstring || fault.Reason?.Text;

    // Map SOAP fault codes to user messages
    const errorMap: Record<string, string> = {
      'Client.AuthenticationFailed': 'Hubo un problema de autenticacion con el sistema.',
      'Client.InvalidData': 'Los datos proporcionados no son validos.',
      'Server.DatabaseError': 'El sistema no esta disponible temporalmente.',
      'Server.Timeout': 'La consulta tomo demasiado tiempo. Intentemos de nuevo.',
    };

    return {
      code: faultCode,
      userMessage: errorMap[faultCode] || 'Ocurrio un error al procesar tu solicitud.',
      recoverable: faultCode?.startsWith('Server'),
    };
  }

  // XML parsing error
  if (error.message?.includes('XML') || error.message?.includes('parse')) {
    return {
      code: 'XML_PARSE_ERROR',
      userMessage: 'Recibimos una respuesta inesperada del sistema.',
      recoverable: true,
    };
  }

  return {
    code: 'UNKNOWN_SOAP_ERROR',
    userMessage: 'Ocurrio un error inesperado. Por favor intenta de nuevo.',
    recoverable: true,
  };
}
```

#### Authentication Failures
```typescript
class CEAAuthManager {
  private token: string | null = null;
  private tokenExpiry: Date | null = null;

  async getValidToken(): Promise<string> {
    if (this.token && this.tokenExpiry && this.tokenExpiry > new Date()) {
      return this.token;
    }

    try {
      const response = await this.authenticate();
      this.token = response.token;
      this.tokenExpiry = new Date(response.expiresAt);
      return this.token;
    } catch (error) {
      logger.error('CEA authentication failed', { error });
      throw new ServiceUnavailableError(
        'No pudimos conectar con el sistema de agua. Por favor intenta en unos minutos.'
      );
    }
  }

  async executeWithAuth<T>(operation: () => Promise<T>): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      if (isAuthenticationError(error)) {
        // Clear token and retry once
        this.token = null;
        await this.getValidToken();
        return operation();
      }
      throw error;
    }
  }
}
```

### 5.2 REST APIs

#### HTTP Status Code Mapping
```typescript
const HTTP_ERROR_MAP: Record<number, ErrorMapping> = {
  // 4xx Client Errors
  400: {
    code: 'BAD_REQUEST',
    message: 'Los datos enviados no son correctos. Por favor verifica e intenta de nuevo.',
    recoverable: false,
  },
  401: {
    code: 'UNAUTHORIZED',
    message: 'Tu sesion ha expirado. Por favor identifiquete nuevamente.',
    recoverable: false,
    action: 'reauthenticate',
  },
  403: {
    code: 'FORBIDDEN',
    message: 'No tienes permiso para realizar esta accion.',
    recoverable: false,
  },
  404: {
    code: 'NOT_FOUND',
    message: 'No encontramos lo que buscas. Verifica los datos proporcionados.',
    recoverable: false,
  },
  409: {
    code: 'CONFLICT',
    message: 'Esta operacion ya fue realizada anteriormente.',
    recoverable: false,
  },
  422: {
    code: 'VALIDATION_ERROR',
    message: 'Algunos datos no son validos. Por favor revisa y corrige.',
    recoverable: false,
  },
  429: {
    code: 'RATE_LIMITED',
    message: 'Estamos procesando muchas solicitudes. Por favor espera un momento.',
    recoverable: true,
    retryAfter: 'Retry-After header or 60 seconds',
  },

  // 5xx Server Errors
  500: {
    code: 'INTERNAL_ERROR',
    message: 'Ocurrio un error en el servidor. Estamos trabajando para solucionarlo.',
    recoverable: true,
  },
  502: {
    code: 'BAD_GATEWAY',
    message: 'No pudimos conectar con el servicio. Intentando de nuevo...',
    recoverable: true,
  },
  503: {
    code: 'SERVICE_UNAVAILABLE',
    message: 'El servicio no esta disponible temporalmente. Por favor intenta en unos minutos.',
    recoverable: true,
  },
  504: {
    code: 'GATEWAY_TIMEOUT',
    message: 'La solicitud tomo demasiado tiempo. Intentemos de nuevo.',
    recoverable: true,
  },
};

function mapHttpError(response: Response): UserFacingError {
  const mapping = HTTP_ERROR_MAP[response.status];

  if (!mapping) {
    return {
      code: 'UNKNOWN_HTTP_ERROR',
      message: 'Ocurrio un error inesperado. Por favor intenta de nuevo.',
      recoverable: response.status >= 500,
    };
  }

  return {
    ...mapping,
    originalStatus: response.status,
  };
}
```

#### Rate Limit Handling
```typescript
class RateLimitHandler {
  private requestCounts: Map<string, { count: number; resetTime: number }> = new Map();

  async executeWithRateLimit<T>(
    key: string,
    operation: () => Promise<Response>,
    config: RateLimitConfig
  ): Promise<T> {
    // Check local rate limit
    const current = this.requestCounts.get(key);
    if (current && current.count >= config.maxRequests && Date.now() < current.resetTime) {
      const waitTime = current.resetTime - Date.now();
      throw new RateLimitError(
        'Estamos procesando muchas solicitudes. Por favor espera un momento.',
        waitTime
      );
    }

    const response = await operation();

    // Handle 429 response
    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      const resetTime = Date.now() + (retryAfter * 1000);

      this.requestCounts.set(key, {
        count: config.maxRequests,
        resetTime
      });

      throw new RateLimitError(
        'Hemos alcanzado el limite de solicitudes. Intentaremos de nuevo en unos segundos.',
        retryAfter * 1000
      );
    }

    // Update counter
    const newCount = (current?.count || 0) + 1;
    const resetTime = current?.resetTime || (Date.now() + config.windowMs);
    this.requestCounts.set(key, { count: newCount, resetTime });

    return response.json();
  }
}
```

### 5.3 External Services

#### Payment Gateway Errors
```typescript
const PAYMENT_ERROR_MAP: Record<string, PaymentErrorResponse> = {
  // Card Issues
  'insufficient_funds': {
    message: 'Fondos insuficientes. Por favor verifica tu saldo o usa otra forma de pago.',
    action: 'suggest_alternative_payment',
  },
  'card_declined': {
    message: 'Tu tarjeta fue rechazada. Contacta a tu banco o usa otra tarjeta.',
    action: 'retry_with_different_card',
  },
  'expired_card': {
    message: 'Tu tarjeta ha expirado. Por favor usa una tarjeta vigente.',
    action: 'retry_with_different_card',
  },
  'invalid_card': {
    message: 'El numero de tarjeta no es valido. Por favor verificalo.',
    action: 'retry_with_correction',
  },
  'invalid_cvv': {
    message: 'El codigo de seguridad (CVV) no es correcto. Son los 3 digitos al reverso de tu tarjeta.',
    action: 'retry_with_correction',
  },

  // Processing Issues
  'processing_error': {
    message: 'Hubo un problema al procesar el pago. No se realizo ningun cargo. Intenta de nuevo.',
    action: 'retry',
  },
  'timeout': {
    message: 'La conexion con el banco tomo mucho tiempo. No se realizo cargo. Deseas intentar de nuevo?',
    action: 'retry',
  },
  'duplicate_transaction': {
    message: 'Parece que este pago ya fue procesado. Verifica tu estado de cuenta.',
    action: 'verify_payment_status',
  },

  // Fraud Prevention
  'fraud_suspected': {
    message: 'Por seguridad, necesitamos verificar esta transaccion. Por favor contacta a tu banco.',
    action: 'contact_bank',
  },
  '3ds_failed': {
    message: 'La verificacion de seguridad no se completo. Intenta de nuevo y sigue las instrucciones de tu banco.',
    action: 'retry_with_3ds',
  },
};

async function handlePaymentError(
  error: PaymentGatewayError,
  context: PaymentContext
): Promise<ChatResponse> {
  const mapping = PAYMENT_ERROR_MAP[error.code];

  // Log for monitoring (never expose to user)
  logger.error('Payment failed', {
    errorCode: error.code,
    gatewayResponse: error.rawResponse,
    transactionId: context.transactionId,
    userId: context.userId,
    // Mask sensitive data
    last4: context.cardNumber?.slice(-4),
  });

  if (!mapping) {
    return {
      message: 'No pudimos procesar el pago en este momento. Puedes intentar de nuevo o visitar nuestras oficinas.',
      actions: ['retry', 'show_office_locations'],
    };
  }

  return {
    message: mapping.message,
    actions: [mapping.action],
    metadata: {
      canRetry: ['retry', 'retry_with_correction', 'retry_with_different_card'].includes(mapping.action),
      requiresHuman: mapping.action === 'verify_payment_status',
    },
  };
}
```

#### Third-Party API Failures
```typescript
interface ExternalServiceConfig {
  name: string;
  primaryEndpoint: string;
  fallbackEndpoint?: string;
  timeout: number;
  circuitBreaker: CircuitBreakerConfig;
}

class ExternalServiceClient {
  private circuitBreaker: CircuitBreaker;

  async call<T>(config: ExternalServiceConfig, request: ApiRequest): Promise<T> {
    // Try primary endpoint with circuit breaker
    try {
      return await this.circuitBreaker.execute(
        () => this.makeRequest(config.primaryEndpoint, request, config.timeout)
      );
    } catch (error) {
      // If circuit is open or primary failed, try fallback
      if (config.fallbackEndpoint) {
        logger.warn('Primary endpoint failed, trying fallback', {
          service: config.name,
          error: error.message,
        });

        try {
          return await this.makeRequest(
            config.fallbackEndpoint,
            request,
            config.timeout
          );
        } catch (fallbackError) {
          logger.error('Fallback endpoint also failed', {
            service: config.name,
            error: fallbackError.message,
          });
        }
      }

      throw new ServiceUnavailableError(
        `El servicio de ${config.name} no esta disponible temporalmente. Por favor intenta en unos minutos.`
      );
    }
  }
}
```

#### Network Issues
```typescript
function isNetworkError(error: any): boolean {
  return (
    error.code === 'ECONNREFUSED' ||
    error.code === 'ENOTFOUND' ||
    error.code === 'ETIMEDOUT' ||
    error.code === 'ECONNRESET' ||
    error.code === 'EPIPE' ||
    error.message?.includes('network') ||
    error.message?.includes('socket')
  );
}

function handleNetworkError(error: any, serviceName: string): UserFacingError {
  logger.error('Network error', {
    service: serviceName,
    code: error.code,
    message: error.message,
  });

  return {
    code: 'NETWORK_ERROR',
    message: `No pudimos conectar con el servicio de ${serviceName}. Verifica tu conexion a internet e intenta de nuevo.`,
    recoverable: true,
    suggestedWait: 5000, // 5 seconds
  };
}
```

---

## 6. Conversation Recovery Patterns

### 6.1 State Recovery

```typescript
interface ConversationState {
  lastValidState: {
    intent: string;
    entities: Record<string, any>;
    step: number;
    timestamp: Date;
  };
  errorCount: number;
  recoveryAttempts: number;
}

class ConversationRecovery {
  async recoverFromError(
    state: ConversationState,
    error: Error
  ): Promise<RecoveryAction> {
    state.errorCount++;

    // First error: Retry with user waiting
    if (state.errorCount === 1) {
      return {
        action: 'retry_silently',
        message: 'Un momento por favor...',
        showLoading: true,
      };
    }

    // Second error: Inform and retry
    if (state.errorCount === 2) {
      return {
        action: 'retry_with_notice',
        message: 'Sigue tomando un poco mas de tiempo. Gracias por esperar...',
        showLoading: true,
      };
    }

    // Third error: Offer options
    if (state.errorCount === 3) {
      return {
        action: 'offer_alternatives',
        message: `Estamos teniendo dificultades. Puedo:
1. Seguir intentando
2. Guardar tu solicitud para procesarla despues
3. Conectarte con un agente
Que prefieres?`,
        options: ['retry', 'queue', 'escalate'],
      };
    }

    // More than 3: Force escalation
    return {
      action: 'force_escalate',
      message: 'Te conecto con un agente que podra ayudarte mejor.',
      transferContext: this.buildTransferContext(state),
    };
  }

  private buildTransferContext(state: ConversationState): TransferContext {
    return {
      intent: state.lastValidState.intent,
      collectedData: state.lastValidState.entities,
      errorHistory: this.getRecentErrors(),
      conversationSummary: this.generateSummary(state),
    };
  }
}
```

### 6.2 Conversation Flow Patterns

```typescript
const RECOVERY_FLOWS = {
  // Pattern: Repeat last valid state
  repeatLastState: {
    trigger: 'user_confusion',
    response: (state: ConversationState) => {
      const lastPrompt = state.lastValidState.lastBotMessage;
      return `Permíteme repetir: ${lastPrompt}`;
    },
  },

  // Pattern: Offer to start over
  startOver: {
    trigger: 'user_request_or_too_many_errors',
    response: () => {
      return `Sin problema, empecemos de nuevo. En que te puedo ayudar?`;
    },
    action: 'clear_state',
  },

  // Pattern: Save progress for later
  saveProgress: {
    trigger: 'system_unavailable',
    response: (state: ConversationState) => {
      const savedId = generateSaveId();
      return `He guardado tu progreso con el codigo ${savedId}.
Cuando quieras continuar, solo dime "continuar ${savedId}"
o vuelve a empezar cuando el sistema este disponible.`;
    },
    action: 'persist_state',
  },

  // Pattern: Human handoff
  humanHandoff: {
    trigger: 'escalation_needed',
    response: (state: ConversationState) => {
      return `Entiendo que esto puede ser frustrante.
Te conecto con un agente que tendra todo el contexto
de nuestra conversacion. Un momento por favor.`;
    },
    action: 'transfer_to_agent',
    transferData: ['conversation_history', 'collected_entities', 'error_log'],
  },
};
```

### 6.3 Progressive Assistance

```typescript
class ProgressiveAssistant {
  private assistanceLevel = 0;

  async handleUserInput(input: string, context: ConversationContext): Promise<Response> {
    const understanding = await this.nlu.process(input);

    if (understanding.confidence < CONFIDENCE_THRESHOLD) {
      this.assistanceLevel++;
      return this.provideProgressiveHelp(understanding, context);
    }

    // Reset on successful understanding
    this.assistanceLevel = 0;
    return this.processIntent(understanding);
  }

  private provideProgressiveHelp(
    understanding: NLUResult,
    context: ConversationContext
  ): Response {
    switch (this.assistanceLevel) {
      case 1:
        // Level 1: Ask for clarification
        return {
          message: 'No estoy seguro de entender. Puedes decirlo de otra manera?',
          suggestions: understanding.alternativeIntents?.slice(0, 3),
        };

      case 2:
        // Level 2: Offer specific options
        const likelyOptions = this.inferLikelyOptions(context);
        return {
          message: 'Ayúdame a entenderte mejor. Quieres:',
          buttons: likelyOptions.map(opt => ({
            label: opt.label,
            value: opt.intent,
          })),
        };

      case 3:
        // Level 3: Show menu
        return {
          message: 'Aqui estan las opciones disponibles:',
          menu: this.getContextualMenu(context),
          hint: 'Selecciona una opcion o escribe lo que necesitas.',
        };

      default:
        // Level 4+: Human handoff
        return {
          message: 'Parece que no logro entenderte bien. Te conecto con un agente.',
          action: 'escalate',
        };
    }
  }
}
```

---

## 7. Logging and Monitoring

### 7.1 Error Event Structure

```typescript
interface ErrorEvent {
  // Identification
  eventId: string;
  timestamp: Date;
  environment: 'production' | 'staging' | 'development';

  // Error Details
  error: {
    code: string;
    type: 'transient' | 'permanent' | 'system' | 'user';
    message: string;
    stack?: string; // Only in non-production
  };

  // Context
  context: {
    conversationId: string;
    userId?: string;
    sessionId: string;
    intent?: string;
    service: string;
    operation: string;
  };

  // Request Details (sanitized)
  request: {
    method?: string;
    endpoint?: string;
    // Never log: passwords, card numbers, full CURPs
    sanitizedParams?: Record<string, any>;
  };

  // Response Details
  response?: {
    statusCode?: number;
    duration: number;
    size?: number;
  };

  // Recovery
  recovery: {
    attempted: boolean;
    strategy?: string;
    successful?: boolean;
    escalated?: boolean;
  };

  // Impact
  impact: {
    severity: 'critical' | 'high' | 'medium' | 'low';
    userFacing: boolean;
    dataLoss: boolean;
  };
}

// Example implementation
function logError(error: Error, context: ErrorContext): void {
  const event: ErrorEvent = {
    eventId: generateUUID(),
    timestamp: new Date(),
    environment: process.env.NODE_ENV as any,

    error: {
      code: error.code || 'UNKNOWN',
      type: classifyError(error),
      message: error.message,
      stack: process.env.NODE_ENV !== 'production' ? error.stack : undefined,
    },

    context: {
      conversationId: context.conversationId,
      userId: context.userId,
      sessionId: context.sessionId,
      intent: context.intent,
      service: context.service,
      operation: context.operation,
    },

    request: {
      method: context.request?.method,
      endpoint: context.request?.endpoint,
      sanitizedParams: sanitizeParams(context.request?.params),
    },

    response: context.response ? {
      statusCode: context.response.status,
      duration: context.response.duration,
      size: context.response.size,
    } : undefined,

    recovery: {
      attempted: false, // Will be updated
      strategy: undefined,
      successful: undefined,
      escalated: undefined,
    },

    impact: {
      severity: determineSeverity(error, context),
      userFacing: context.userFacing ?? true,
      dataLoss: false,
    },
  };

  logger.error(event);

  // Send to monitoring system
  monitoring.trackError(event);
}
```

### 7.2 Alert Thresholds

```typescript
const ALERT_CONFIG = {
  // Critical Alerts (PagerDuty/SMS)
  critical: {
    errorRateThreshold: 0.1,      // >10% error rate
    consecutiveFailures: 5,        // 5 failures in a row
    services: ['payment', 'cea'],  // Critical services
    responseTime: 30000,           // >30s response
  },

  // High Priority Alerts (Slack #alerts)
  high: {
    errorRateThreshold: 0.05,     // >5% error rate
    consecutiveFailures: 10,
    circuitBreakerOpen: true,     // Any circuit breaker opens
    responseTime: 15000,          // >15s response
  },

  // Medium Priority (Slack #monitoring)
  medium: {
    errorRateThreshold: 0.02,     // >2% error rate
    cacheHitRateBelowThreshold: 0.7, // Cache hit <70%
    responseTime: 10000,          // >10s response
  },

  // Low Priority (Daily digest)
  low: {
    unusualPatterns: true,
    deprecationWarnings: true,
    performanceDegradation: true,
  },
};

// Alert rules
const ALERT_RULES = [
  {
    name: 'High Error Rate',
    condition: (metrics) => metrics.errorRate > ALERT_CONFIG.critical.errorRateThreshold,
    severity: 'critical',
    message: (metrics) => `Error rate at ${(metrics.errorRate * 100).toFixed(1)}% (threshold: 10%)`,
    channels: ['pagerduty', 'slack-alerts'],
  },
  {
    name: 'Circuit Breaker Open',
    condition: (metrics) => metrics.circuitBreakers.some(cb => cb.state === 'OPEN'),
    severity: 'high',
    message: (metrics) => `Circuit breaker open for: ${metrics.circuitBreakers.filter(cb => cb.state === 'OPEN').map(cb => cb.service).join(', ')}`,
    channels: ['slack-alerts'],
  },
  {
    name: 'Payment Failures',
    condition: (metrics) => metrics.paymentFailures > 3,
    severity: 'high',
    message: (metrics) => `${metrics.paymentFailures} payment failures in last 15 minutes`,
    channels: ['slack-alerts', 'email-finance'],
  },
];
```

### 7.3 Dashboard Requirements

```typescript
const DASHBOARD_PANELS = {
  // Real-time Overview
  overview: {
    metrics: [
      'total_requests',
      'error_rate',
      'average_response_time',
      'active_conversations',
    ],
    timeRange: '1h',
    refreshRate: '30s',
  },

  // Error Analysis
  errors: {
    panels: [
      {
        type: 'timeseries',
        title: 'Errors by Type',
        metric: 'error_count',
        groupBy: 'error_type',
      },
      {
        type: 'table',
        title: 'Top Errors',
        metric: 'error_count',
        groupBy: 'error_code',
        limit: 10,
      },
      {
        type: 'heatmap',
        title: 'Error Distribution by Service',
        metric: 'error_count',
        xAxis: 'service',
        yAxis: 'hour',
      },
    ],
  },

  // Service Health
  services: {
    panels: [
      {
        type: 'gauge',
        title: 'Service Availability',
        metric: 'availability',
        thresholds: { red: 0.95, yellow: 0.99 },
      },
      {
        type: 'status',
        title: 'Circuit Breaker Status',
        services: ['cea', 'sat', 'payment', 'transit'],
      },
      {
        type: 'histogram',
        title: 'Response Time Distribution',
        metric: 'response_time',
        buckets: [100, 500, 1000, 2000, 5000, 10000],
      },
    ],
  },

  // Recovery Metrics
  recovery: {
    panels: [
      {
        type: 'stat',
        title: 'Retry Success Rate',
        metric: 'retry_success_rate',
      },
      {
        type: 'timeseries',
        title: 'Escalations to Human',
        metric: 'escalation_count',
      },
      {
        type: 'table',
        title: 'Failed Recovery Attempts',
        filters: { recovery_successful: false },
      },
    ],
  },
};
```

### 7.4 Debugging Information

```typescript
interface DebugContext {
  // Trace ID for distributed tracing
  traceId: string;
  spanId: string;
  parentSpanId?: string;

  // Timing
  timestamps: {
    received: Date;
    processed: Date;
    responded: Date;
  };

  // Processing steps
  steps: Array<{
    name: string;
    duration: number;
    result: 'success' | 'failure' | 'skipped';
    details?: any;
  }>;

  // External calls
  externalCalls: Array<{
    service: string;
    endpoint: string;
    method: string;
    duration: number;
    status: number;
    cached: boolean;
  }>;

  // Feature flags
  featureFlags: Record<string, boolean>;

  // A/B test variants
  experiments: Record<string, string>;
}

// Debug endpoint (internal only)
app.get('/debug/conversation/:id', authenticate, authorize('admin'), async (req, res) => {
  const debugInfo = await getDebugContext(req.params.id);
  res.json({
    ...debugInfo,
    // Additional debugging info
    relatedErrors: await getRelatedErrors(debugInfo.traceId),
    conversationHistory: await getConversationHistory(req.params.id),
    systemState: await getSystemStateSnapshot(debugInfo.timestamps.received),
  });
});
```

---

## 8. Testing Error Scenarios

### 8.1 Chaos Engineering Approaches

```typescript
// Chaos Testing Configuration
const CHAOS_CONFIG = {
  enabled: process.env.CHAOS_ENABLED === 'true',
  probability: 0.05, // 5% of requests

  scenarios: {
    latency: {
      enabled: true,
      minDelay: 1000,
      maxDelay: 10000,
      probability: 0.3,
    },
    failure: {
      enabled: true,
      statusCodes: [500, 502, 503, 504],
      probability: 0.2,
    },
    timeout: {
      enabled: true,
      probability: 0.1,
    },
    partialFailure: {
      enabled: true,
      corruptionProbability: 0.05,
      probability: 0.1,
    },
  },

  // Only chaos test these services
  targetServices: ['cea-mock', 'sat-mock'],

  // Never chaos test these
  excludedServices: ['payment', 'production-apis'],
};

class ChaosMiddleware {
  async inject(request: Request, next: () => Promise<Response>): Promise<Response> {
    if (!this.shouldInjectChaos(request)) {
      return next();
    }

    const scenario = this.selectScenario();

    switch (scenario) {
      case 'latency':
        await this.injectLatency();
        return next();

      case 'failure':
        throw new ChaosInjectedError(this.randomStatusCode());

      case 'timeout':
        await new Promise(() => {}); // Never resolves

      case 'partialFailure':
        const response = await next();
        return this.corruptResponse(response);

      default:
        return next();
    }
  }
}
```

### 8.2 Error Injection Patterns

```typescript
// Test utilities for error injection
class ErrorInjector {
  // Inject specific error types
  static injectTransientError(service: string): void {
    mockService(service).nextResponse({
      status: 503,
      body: { error: 'Service temporarily unavailable' },
    });
  }

  static injectTimeoutError(service: string, delayMs: number): void {
    mockService(service).delay(delayMs);
  }

  static injectValidationError(service: string, field: string): void {
    mockService(service).nextResponse({
      status: 400,
      body: {
        error: 'Validation failed',
        field: field,
        message: `Invalid ${field}`,
      },
    });
  }

  static injectPartialSuccess(service: string): void {
    mockService(service).nextResponse({
      status: 207, // Multi-status
      body: {
        results: [
          { id: 1, status: 'success' },
          { id: 2, status: 'failed', error: 'Not found' },
        ],
      },
    });
  }

  static injectCircuitBreakerTrip(service: string): void {
    // Inject enough failures to trip circuit breaker
    const failureCount = 5;
    for (let i = 0; i < failureCount; i++) {
      mockService(service).queueResponse({
        status: 500,
        body: { error: 'Internal server error' },
      });
    }
  }
}

// Example test
describe('Error Handling', () => {
  describe('CEA Service Errors', () => {
    it('should retry transient errors with backoff', async () => {
      ErrorInjector.injectTransientError('cea');
      ErrorInjector.injectTransientError('cea');
      // Third call succeeds
      mockService('cea').nextResponse({
        status: 200,
        body: { balance: 450.50 },
      });

      const result = await ceaService.getBalance('1234567890');

      expect(result.balance).toBe(450.50);
      expect(mockService('cea').callCount).toBe(3);
    });

    it('should show user-friendly message after max retries', async () => {
      // All calls fail
      for (let i = 0; i < 5; i++) {
        ErrorInjector.injectTransientError('cea');
      }

      const response = await chatbot.processMessage('cual es mi saldo?');

      expect(response.message).toContain('no esta disponible temporalmente');
      expect(response.options).toContain('retry');
      expect(response.options).toContain('escalate');
    });

    it('should trip circuit breaker after threshold', async () => {
      ErrorInjector.injectCircuitBreakerTrip('cea');

      // Try to make another call
      await expect(ceaService.getBalance('1234567890'))
        .rejects.toThrow(CircuitOpenError);

      // Verify circuit breaker state
      expect(ceaService.circuitBreaker.state).toBe('OPEN');
    });
  });
});
```

### 8.3 Load Testing for Failures

```typescript
// k6 load test script for error scenarios
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const recoveryTime = new Trend('recovery_time');

export const options = {
  scenarios: {
    // Normal load
    normal: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
    },
    // Spike to trigger errors
    spike: {
      executor: 'ramping-vus',
      startVUs: 50,
      stages: [
        { duration: '1m', target: 200 },
        { duration: '2m', target: 200 },
        { duration: '1m', target: 50 },
      ],
      startTime: '5m',
    },
    // Sustained high load
    stress: {
      executor: 'constant-vus',
      vus: 150,
      duration: '10m',
      startTime: '9m',
    },
  },
  thresholds: {
    errors: ['rate<0.1'],           // Error rate < 10%
    http_req_duration: ['p(95)<5000'], // 95% of requests < 5s
    recovery_time: ['p(95)<10000'],    // 95% recovery < 10s
  },
};

export default function() {
  // Simulate chatbot interaction
  const conversationId = `conv_${__VU}_${__ITER}`;

  // Start conversation
  let response = http.post('/api/chat', JSON.stringify({
    conversationId,
    message: 'quiero consultar mi saldo de agua',
  }));

  check(response, {
    'start conversation success': (r) => r.status === 200,
  });

  if (response.status !== 200) {
    errorRate.add(1);

    // Measure recovery time
    const startRecovery = Date.now();
    let recovered = false;

    for (let i = 0; i < 5 && !recovered; i++) {
      sleep(2);
      response = http.post('/api/chat', JSON.stringify({
        conversationId,
        message: 'intentar de nuevo',
      }));

      if (response.status === 200) {
        recovered = true;
        recoveryTime.add(Date.now() - startRecovery);
      }
    }

    return;
  }

  errorRate.add(0);

  // Continue with account number
  sleep(1);
  response = http.post('/api/chat', JSON.stringify({
    conversationId,
    message: '1234567890',
  }));

  check(response, {
    'account lookup success': (r) => r.status === 200,
    'balance returned': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.message && body.message.includes('$');
      } catch {
        return false;
      }
    },
  });

  sleep(Math.random() * 3);
}
```

### 8.4 Error Scenario Test Matrix

| Scenario | Test Type | Expected Behavior | Acceptance Criteria |
|----------|-----------|-------------------|---------------------|
| API Timeout (5s) | Integration | Retry 3x with backoff | User sees message within 20s |
| API Timeout (30s) | Integration | Quick fail, inform user | User informed within 5s |
| Invalid CURP | Unit | Clear error message | Specific format guidance shown |
| Service Down | Integration | Circuit breaker activates | Fallback response served |
| Rate Limited | Load | Graceful queuing | No requests lost |
| Concurrent Failures | Chaos | Prioritized recovery | Critical services recover first |
| Partial Response | Integration | Handle incomplete data | Show available data + disclaimer |
| Auth Token Expired | Integration | Silent refresh | User unaware of refresh |
| Database Connection Lost | Integration | Queue requests | Process when restored |
| Memory Pressure | Load | Graceful degradation | No OOM crashes |

---

## 9. Implementation Checklist

### Phase 1: Foundation (Week 1-2)
- [ ] Implement base error classification system
- [ ] Create error message templates (Spanish)
- [ ] Set up centralized error logging
- [ ] Configure basic retry logic with exponential backoff

### Phase 2: Resilience Patterns (Week 3-4)
- [ ] Implement circuit breakers for all external services
- [ ] Set up caching layer for graceful degradation
- [ ] Create fallback responses for each service
- [ ] Implement request queuing for deferred processing

### Phase 3: User Experience (Week 5-6)
- [ ] Implement progressive error assistance
- [ ] Set up conversation state recovery
- [ ] Create human handoff flow with context transfer
- [ ] A/B test error message effectiveness

### Phase 4: Monitoring & Testing (Week 7-8)
- [ ] Deploy monitoring dashboards
- [ ] Configure alerting rules
- [ ] Run chaos engineering experiments
- [ ] Load test error scenarios
- [ ] Document runbooks for common errors

---

## Sources

### Chatbot Error Handling
- [10 Chatbot Error Handling & Recovery Strategies](https://allgpts.co/blog/10-chatbot-error-handling-and-recovery-strategies/)
- [7 Chatbot Error Handling Strategies for Better UX](https://quidget.ai/blog/ai-automation/7-chatbot-error-handling-strategies-for-better-ux/)
- [ChatbotGen: 10 Critical Chat Bot Best Practices for 2025](https://www.chatbotgen.com/blog/chat-bot-best-practices)
- [7 Essential Chat Bot Best Practices for 2025](https://www.spurnow.com/en/blogs/chat-bot-best-practices)
- [How to design conversation fallback and error handling strategies - Tencent Cloud](https://www.tencentcloud.com/techpedia/127616)
- [Chatbot Error Handling - Managing Mistakes and Improving AI Response Accuracy](https://moldstud.com/articles/p-chatbot-error-handling-managing-mistakes-and-improving-accuracy-in-ai-responses)

### API Resilience Patterns
- [Resilient APIs: Retry Logic, Circuit Breakers, and Fallback Mechanisms](https://medium.com/@fahimad/resilient-apis-retry-logic-circuit-breakers-and-fallback-mechanisms-cfd37f523f43)
- [AWS Builders Library: Timeouts, retries and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [AWS Prescriptive Guidance: Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)
- [Mastering Exponential Backoff in Distributed Systems - Better Stack](https://betterstack.com/community/guides/monitoring/exponential-backoff/)
- [Understanding Retry Pattern With Exponential Back-Off and Circuit Breaker - DZone](https://dzone.com/articles/understanding-retry-pattern-with-exponential-back)
- [Build Resilient API Clients: Retry and Circuit Breaker Patterns - Atomic Object](https://spin.atomicobject.com/retry-circuit-breaker-patterns/)
- [Efficient Fault Tolerance with Circuit Breaker Pattern - Aerospike](https://aerospike.com/blog/circuit-breaker-pattern/)

### REST API Error Handling
- [Best Practices for Consistent API Error Handling - Zuplo](https://zuplo.com/learning-center/best-practices-for-api-error-handling)
- [Errors Best Practices in REST API Design - Speakeasy](https://www.speakeasy.com/api-design/errors)
- [Best Practices for API Error Handling - Postman Blog](https://blog.postman.com/best-practices-for-api-error-handling/)
- [REST API Error Handling: Best Practices and Status Codes - APILayer](https://blog.apilayer.com/best-practices-for-rest-api-error-handling-in-2025/)
- [Best Practices for REST API Error Handling - Baeldung](https://www.baeldung.com/rest-api-error-handling-best-practices)

### SOAP API Error Handling
- [SOAP Error Codes - Understanding Their Meanings and Resolution Strategies](https://moldstud.com/articles/p-soap-error-codes-understanding-their-meanings-and-resolution-strategies)
- [Error Handling with SOAP Faults - O'Reilly](https://www.oreilly.com/library/view/java-web-services/0596002696/ch04s02.html)
- [Error Handling in SOAP to REST: Best Practices - DreamFactory](https://blog.dreamfactory.com/error-handling-in-soap-to-rest-best-practices)

### Chatbot UX Design
- [14 Best Practices for Designing Effective Chatbots and Voice Assistants - UXness](https://www.uxness.in/2024/07/ai-chatbot-design-best-practices.html)
- [Chatbot UX Design: Complete Guide 2025 - Parallel](https://www.parallelhq.com/blog/chatbot-ux-design)
- [Nine UX best practices for AI chatbots - Mind the Product](https://www.mindtheproduct.com/deep-dive-ux-best-practices-for-ai-chatbots/)
- [Conversational UX - What a user-friendly design looks like - BotFriends](https://botfriends.de/en/blog/fehlermeldungen-bei-chatbots/)
- [Top Chatbot UX Tips and Best Practices for 2025 - Netguru](https://www.netguru.com/blog/chatbot-ux-tips)

### Government Chatbots
- [Empowering Agencies with Chatbot for Government Services - VIDIZMO](https://vidizmo.ai/blog/chatbot-for-government-services)
- [Chatbots in the Public Sector - FXMedia](https://www.fxmweb.com/insights/chatbots-in-the-public-sector-how-ai-driven-chatbots-are-reshaping-government-services.html)
- [Government Chatbot: Top Use Case Examples and Benefits - Streebo](https://www.streebo.com/chatbot-for-government)
- [How local governments can use AI-powered chatbots - Granicus](https://granicus.com/blog/how-local-governments-can-use-ai-powered-chatbots/)
- [Citibot: AI Resident Engagement Solutions for Government](https://www.citibot.io)

### Observability & Monitoring
- [Chatbot Monitoring with Advanced Observability - Langfuse](https://langfuse.com/faq/all/chatbot-analytics)
- [AI Observability: A Complete Guide for 2026 - UptimeRobot](https://uptimerobot.com/knowledge-hub/observability/ai-observability-the-complete-guide/)
- [LLM Observability: Best Practices for 2025 - Maxim AI](https://www.getmaxim.ai/articles/llm-observability-best-practices-for-2025/)
- [AI Agent Monitoring: Best Practices, Tools, and Metrics - UptimeRobot](https://uptimerobot.com/knowledge-hub/monitoring/ai-agent-monitoring-best-practices-tools-and-metrics/)
- [AI Agent Observability - OpenTelemetry](https://opentelemetry.io/blog/2025/ai-agent-observability/)
- [Datadog LLM Observability](https://docs.datadoghq.com/llm_observability/)

### Payment Gateway Error Handling
- [Payment Gateway Failure? Here's How to Fix It Fast - Abbacus](https://www.abbacustechnologies.com/payment-gateway-failure-heres-how-to-fix-it-fast/)
- [How to Handle Payment Failures and Retry Logic](https://medium.com/@mallikarjunpasupuleti/how-to-handle-payment-failures-and-retry-logic-in-your-application-ab878e2d8849)
- [Online Payment Failure: Reasons & How to Handle Them - Razorpay](https://razorpay.com/blog/online-payments-failure-reasons/)
- [Payment Gateway Integration Guide - Pine Labs](https://www.pinelabs.com/blog/payment-gateway-integration-explained-api-setup-webhooks-and-error-handling-for-developers)

### Human Handoff & Escalation
- [When to hand off to a human: How to set effective AI escalation rules - Replicant](https://www.replicant.com/blog/when-to-hand-off-to-a-human-how-to-set-effective-ai-escalation-rules)
- [Chatbot to Human Handoff: Complete Guide 2025 - SpurNow](https://www.spurnow.com/en/blogs/chatbot-to-human-handoff)
- [Escalation Done Right: Best Practices for Handing Off from Chatbot to Human - Cobbai](https://cobbai.com/blog/chatbot-escalation-best-practices)
- [Smarter Escalations: AI Handoffs to Humans That Boost CSAT - Robylon](https://www.robylon.ai/blog/smarter-ai-escalations-customer-support)
- [Escalation Design: Why AI Fails at the Handoff - Bucher + Suter](https://www.bucher-suter.com/escalation-design-why-ai-fails-at-the-handoff-not-the-automation/)

### Chaos Engineering
- [Democratizing Chaos Engineering with Fault Injection - k6](https://k6.io/blog/democratize-chaos-testing/)
- [Chaos Engineering: Types, Experiments, and Best Practices - Steadybit](https://steadybit.com/blog/chaos-experiments/)
- [Chaos Engineering Tools in 2024 - DevOps School](https://www.devopsschool.com/blog/chaos-engineering-tools-in-2024/)
- [What is Chaos Engineering? Breaking Systems to Build Resilience - testRigor](https://testrigor.com/blog/what-is-chaos-engineering/)
- [Chaos Engineering with LocalStack](https://docs.localstack.cloud/user-guide/chaos-engineering/)
- [Gremlin Chaos Engineering](https://www.gremlin.com/chaos-engineering)

---

*Document Version: 1.0*
*Last Updated: February 2026*
*Author: MARIA Platform Team - Gobierno de Queretaro*
