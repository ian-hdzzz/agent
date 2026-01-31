# Testing Patterns

**Analysis Date:** 2026-01-31

## Test Framework

**Runner:**
- Custom test scripts (no Jest, Vitest, or Mocha detected)
- Executed with `tsx` (TypeScript executor)

**Assertion Library:**
- Manual assertions using console output and comparisons
- No structured assertion library (no Chai, Expect, or Jest matchers)

**Run Commands:**
```bash
npm run test              # Run main test suite (src/test.ts)
npm run test:api         # Test CEA API integration (src/test-api.ts)
npm run test:api:verbose # Run API tests with verbose output
npm run test:interactive # Run tests in interactive mode
npm run typecheck        # TypeScript type checking
npm run dev              # Development with file watching
npm run build            # TypeScript compilation
```

## Test File Organization

**Location:**
- Test files co-located in `src/` directory alongside source code
- Naming convention: `test.ts`, `test-*.ts` (e.g., `test-api.ts`, `test-ticket.ts`, `test-agent-flows.ts`)
- NOT using separate `test/` or `__tests__/` directory

**Test Files Present:**
- `src/test.ts` - Main test suite (205 lines)
- `src/test-api.ts` - Raw SOAP API testing (325 lines)
- `src/test-ticket.ts` - Ticket creation testing (283 lines)
- `src/test-agent-flows.ts` - Agent workflow testing (228 lines)
- `src/test-all-tickets.ts` - Batch ticket testing (121 lines)

**Directory Structure:**
```
src/
├── agent.ts
├── server.ts
├── tools.ts
├── types.ts
├── context.ts
├── test.ts               # Main test file
├── test-api.ts           # API integration tests
├── test-ticket.ts        # Ticket creation tests
├── test-agent-flows.ts   # Agent workflow tests
└── test-all-tickets.ts   # Batch operations
```

## Test Structure

**Suite Organization:**

Tests are organized in linear scripts without describe/it blocks. Each test has:
1. Header comment with section title
2. Setup section
3. Test execution
4. Console output assertions

Example from `src/test.ts`:
```typescript
async function runTests() {
    console.log("\n╔════════════════════════════════════════════════════════╗");
    console.log("║           CEA Agent Server - Test Suite                ║");
    console.log("╚════════════════════════════════════════════════════════╝\n");

    // Test 1: Ticket Folio Generation
    console.log("📝 Test 1: Ticket Folio Generation");
    console.log("─".repeat(50));

    const folio1 = generateTicketFolio("fuga");
    const folio2 = generateTicketFolio("fuga");

    console.log(`  Folio 1 (fuga):  ${folio1}`);
    console.log(`  Folio 2 (fuga):  ${folio2}`);

    const folioPattern = /^CEA-[A-Z]{3}-\d{6}-\d{4}$/;
    console.log(`  ✅ Format valid: ${folioPattern.test(folio1) && folioPattern.test(folio2)}`);
    console.log(`  ✅ Sequential: ${folio2 > folio1}`);
}
```

**Patterns:**

1. **Setup Phase:**
   ```typescript
   // Load environment
   import { config } from "dotenv";
   config();

   // Import dependencies
   import { runWorkflow } from "./agent.js";
   import { generateTicketFolio, getMexicoDate } from "./tools.js";
   ```

2. **Test Array Pattern:**
   ```typescript
   const testCases = [
       {
           name: "Greeting",
           message: "Hola, buenas tardes",
           expectedClassification: "informacion"
       },
       {
           name: "Payment Query",
           message: "Quiero saber cuánto debo de mi recibo",
           expectedClassification: "pagos"
       },
       // ... more cases
   ];
   ```

3. **Loop-Based Test Execution:**
   ```typescript
   for (const testCase of testCases) {
       console.log(`\n📝 Test ${i + 1}: ${testCase.name}`);
       console.log("─".repeat(50));

       const result = await runWorkflow({
           input_as_text: testCase.message,
           conversationId: `test-${i}`
       });

       const passed = result.classification === testCase.expectedClassification;
       console.log(`  Classification: ${result.classification}`);
       console.log(`  Expected: ${testCase.expectedClassification}`);
       console.log(`  Result: ${passed ? "✅ PASS" : "❌ FAIL"}`);
   }
   ```

4. **Conditional Execution:**
   ```typescript
   // Skip tests if API key missing
   if (!process.env.OPENAI_API_KEY) {
       console.log("⚠️  Skipping workflow tests - OPENAI_API_KEY not set\n");
       return;
   }
   ```

## Manual Testing Patterns

**API Direct Testing (`test-api.ts`):**

Tests raw SOAP API calls without agent layers:
```typescript
// Test contract (use a real one for actual testing)
const TEST_CONTRACT = process.env.TEST_CONTRACT || "123456";

function buildContratoSOAP(contrato: string): string {
    return `<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" ...>
        <soapenv:Body>
            <occ:consultaDetalleContrato>
                <numeroContrato>${contrato}</numeroContrato>
            </occ:consultaDetalleContrato>
        </soapenv:Body>
    </soapenv:Envelope>`;
}

// Call API and log response
const response = await fetch(CEA_API_BASE, {
    method: "POST",
    body: buildContratoSOAP(TEST_CONTRACT),
    headers: { "Content-Type": "text/xml" }
});

const xml = await response.text();
console.log("Raw XML Response:", xml);
```

**Workflow Testing (`test-agent-flows.ts`):**

Tests complete agent workflows with multiple turns:
```typescript
// Simulate multi-turn conversation
const conversationId = crypto.randomUUID();

// Turn 1: User message
const result1 = await runWorkflow({
    input_as_text: "Quiero saber mi saldo",
    conversationId: conversationId
});

// Turn 2: Response with contract
const result2 = await runWorkflow({
    input_as_text: "Mi contrato es 123456",
    conversationId: conversationId
});

console.log(`Turn 1 Classification: ${result1.classification}`);
console.log(`Turn 2 Response: ${result2.response}`);
```

**Ticket Creation Testing (`test-ticket.ts`):**

Tests ticket creation with various service types:
```typescript
const ticketTests = [
    { type: "fuga", title: "Reporte de fuga" },
    { type: "pagos", title: "Solicitud de cambio a recibo digital" },
    { type: "urgente", title: "Reporte urgente" }
];

for (const test of ticketTests) {
    const result = await createTicketDirect({
        service_type: test.type as TicketType,
        titulo: test.title,
        descripcion: "Test ticket"
    });

    console.log(`Ticket Type: ${test.type}`);
    console.log(`Success: ${result.success}`);
    console.log(`Folio: ${result.folio}`);
}
```

## Mocking

**Framework:** Not used - tests use real API calls when credentials are available

**Approach:**
- Skip tests when API keys not available: `if (!process.env.OPENAI_API_KEY) { return; }`
- Use real contract numbers from environment: `TEST_CONTRACT = process.env.TEST_CONTRACT || "123456"`
- Database operations use real PostgreSQL connections via `pg.Pool`

**No Mock Usage:**
- No Sinon, Jest mocks, or vitest mocks
- No mock database libraries
- All external service calls are real (with retry/error handling)

**Pattern: Graceful Degradation**

When API unavailable, tests log warnings but don't fail:
```typescript
try {
    const response = await fetchWithRetry(url, options);
    // ... process response
} catch (error) {
    console.warn(`[API] Attempt ${attempt} error: ${lastError.message}`);
    // Try next attempt or gracefully return error result
}
```

## Fixtures and Factories

**Test Data:**

Fixtures are inline in test files as constants:
```typescript
// From test.ts
const testCases = [
    {
        name: "Greeting",
        message: "Hola, buenas tardes",
        expectedClassification: "informacion"
    },
    {
        name: "Payment Query",
        message: "Quiero saber cuánto debo de mi recibo",
        expectedClassification: "pagos"
    },
    {
        name: "Consumption Query",
        message: "Cuál es mi consumo de agua del mes pasado",
        expectedClassification: "consumos"
    },
    {
        name: "Leak Report",
        message: "Hay una fuga de agua en la calle principal",
        expectedClassification: "fuga"
    },
    // ... more cases
];
```

**Factory-like Functions:**

Utility functions generate test data:
```typescript
// From tools.ts
function generateTicketFolio(ticketType: TicketType): string {
    const typeCode = TICKET_CODES[ticketType];
    const now = getMexicoDate();
    const year = now.getFullYear().toString();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const dateStr = `${year}${month}${day}`;
    const timestamp = now.getTime().toString().slice(-4);
    return `${typeCode}-${dateStr}-${timestamp}`;
}

// Usage in tests
const folio1 = generateTicketFolio("fuga");
const folio2 = generateTicketFolio("fuga");
```

**Location:**
- Test fixtures are co-located inline in test files
- No separate fixtures directory or factory files
- Test data generated at runtime, not stored

## Coverage

**Requirements:** Not enforced - no coverage threshold configuration detected

**View Coverage:**
- Not applicable - coverage tools not configured
- Manual inspection via test output (✅ PASS / ❌ FAIL console logs)

## Test Types

**Unit Tests:**
- **Scope:** Individual utility functions (folio generation, date handling, XML parsing)
- **Approach:** Directly call function, assert return value
- **Example:** `generateTicketFolio("fuga")` → verify format matches `/^CEA-[A-Z]{3}-\d{6}-\d{4}$/`
- **Files:** Inline in `src/test.ts` under "Test 1: Ticket Folio Generation"

**Integration Tests:**
- **Scope:** API calls, database operations, multi-tool workflows
- **Approach:** Call workflow with message, verify classification and response
- **Example:** Call `runWorkflow()` with Spanish message, verify correct agent selected
- **Files:** `src/test-agent-flows.ts`, `src/test-api.ts`, `src/test-ticket.ts`

**E2E Tests:**
- **Framework:** Not used
- **Alternative:** Full workflow tests in `test-agent-flows.ts` simulate end-to-end request→response

## Common Patterns

**Async Testing:**

All async operations await properly:
```typescript
// From test-agent-flows.ts
async function runTests() {
    const result = await runWorkflow({
        input_as_text: "Hola, quiero reportar una fuga",
        conversationId: conversationId
    });

    console.log(`Response: ${result.response}`);
    console.log(`Classification: ${result.classification}`);
}

// Wait for all tests
await runTests();
```

**Error Testing:**

Errors are tested by checking response success/error fields:
```typescript
// From test-ticket.ts
const result = await createTicketDirect({
    service_type: "fuga",
    titulo: "Test",
    descripcion: "Test"
});

if (!result.success) {
    console.log(`❌ Error: ${result.error}`);
} else {
    console.log(`✅ Created ticket: ${result.folio}`);
}
```

**API Response Validation:**

Test parsers by validating returned structure:
```typescript
// From test-api.ts
const response = await fetch(CEA_API_BASE, {
    method: "POST",
    body: buildDeudaSOAP(TEST_CONTRACT)
});

const xml = await response.text();
const parsed = parseDeudaResponse(xml);

console.log(`Total Debt: ${parsed.data?.totalDeuda}`);
console.log(`Overdue: ${parsed.data?.vencido}`);
console.log(`Due Soon: ${parsed.data?.porVencer}`);
```

## Test Execution

**Running Tests:**

```bash
# Main test suite
npm run test

# With interactive prompts
npm run test:interactive

# API integration tests
npm run test:api

# Verbose API output
npm run test:api:verbose
```

**Output Format:**

Tests use visual formatting with emoji and ASCII lines:
```
╔════════════════════════════════════════════════════════╗
║           CEA Agent Server - Test Suite                ║
╚════════════════════════════════════════════════════════╝

📝 Test 1: Ticket Folio Generation
──────────────────────────────────────────────────────────
  Folio 1 (fuga):  CEA-FUG-20260131-4521
  Folio 2 (fuga):  CEA-FUG-20260131-4812
  ✅ Format valid: true
  ✅ Sequential: true

📅 Test 2: Mexico Timezone
──────────────────────────────────────────────────────────
  Current Mexico Time: 2026-01-31T14:30:00Z
  Formatted: viernes, 31 de enero de 2026 14:30
```

## Testing Best Practices in Codebase

**1. Environment-Aware Testing:**
- Skip tests when API keys unavailable
- Use environment-provided test data
- Gracefully handle network failures

**2. Logging Over Assertions:**
- No assertion library; tests use console output for verification
- Human reads logs to verify correctness
- Prefer detailed output over yes/no assertions

**3. Real Integration:**
- Tests use real PostgreSQL and CEA API (when available)
- No test databases or mock APIs
- Retry logic ensures flaky network doesn't break tests

**4. Organized Output:**
- Use visual separators (═, ─, ║)
- Use emoji for quick test status (✅, ❌, ⚠️, 📝, 📅)
- Group related tests under numbered headers

---

*Testing analysis: 2026-01-31*
