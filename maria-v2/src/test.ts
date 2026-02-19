// ============================================
// Maria V2 - Simple Test Suite
// ============================================

import { config } from "dotenv";
config();

import { runWorkflow, getAgentHealth } from "./agent.js";
import { classifyIntent } from "./utils/classifier.js";
import { logger } from "./utils/logger.js";
import { getMemoryStore } from "./utils/memory.js";
import { getCache } from "./utils/cache.js";
import { metrics } from "./utils/metrics.js";

const TESTS = [
    {
        name: "Saludo simple",
        input: "Hola, ¿qué puedes hacer?",
        expectedCategory: "CON"
    },
    {
        name: "Consulta de saldo",
        input: "¿Cuánto debo del contrato 523160?",
        expectedCategory: "CON"
    },
    {
        name: "Reporte de fuga (vía pública)",
        input: "Hay una fuga de agua en la calle",
        expectedCategory: "REP"
    },
    {
        name: "No tengo agua",
        input: "No tengo agua desde ayer",
        expectedCategory: "REP"
    },
    {
        name: "Aclaración de cobro",
        input: "Quiero una aclaración de un cobro excesivo",
        expectedCategory: "FAC"
    },
    {
        name: "Convenio de pago",
        input: "No puedo pagar todo, necesito un plan de pagos",
        expectedCategory: "CVN"
    },
    {
        name: "Cambio de titular",
        input: "Quiero cambiar el nombre del titular",
        expectedCategory: "CTR"
    },
    {
        name: "Consulta de consumo",
        input: "¿Cuál es mi historial de consumo?",
        expectedCategory: "CNS"
    },
    {
        name: "Medidor dañado",
        input: "Mi medidor está goteando",
        expectedCategory: "SRV"
    }
];

async function testClassification() {
    console.log("\n🧪 Testing Classification\n");
    console.log("=".repeat(80));

    let passed = 0;
    let failed = 0;

    for (const test of TESTS) {
        try {
            const result = await classifyIntent(test.input, [], true);
            const success = result.category === test.expectedCategory;

            if (success) {
                passed++;
                console.log(`✅ ${test.name}`);
            } else {
                failed++;
                console.log(`❌ ${test.name}`);
                console.log(`   Expected: ${test.expectedCategory}, Got: ${result.category}`);
            }
            console.log(`   Input: "${test.input.slice(0, 50)}..."`);
            console.log(`   Confidence: ${(result.confidence * 100).toFixed(1)}%`);
            console.log(`   Reasoning: ${result.reasoning.slice(0, 60)}...`);
            console.log();
        } catch (error) {
            failed++;
            console.log(`💥 ${test.name} - Error: ${error}`);
        }
    }

    console.log("=".repeat(80));
    console.log(`Results: ${passed} passed, ${failed} failed (${((passed/TESTS.length)*100).toFixed(1)}%)\n`);

    return { passed, failed, total: TESTS.length };
}

async function testWorkflow() {
    console.log("\n🧪 Testing Full Workflow\n");
    console.log("=".repeat(80));

    const conversationId = `test-${Date.now()}`;

    const testMessages = [
        "Hola",
        "Quiero consultar mi saldo",
        "Mi contrato es el 523160"
    ];

    for (const message of testMessages) {
        try {
            console.log(`\n👤 User: ${message}`);
            const start = Date.now();
            
            const result = await runWorkflow({
                input_as_text: message,
                conversationId,
                metadata: { name: "Test User", phone: "4421234567" }
            });

            const duration = Date.now() - start;
            
            console.log(`🤖 Maria: ${result.output_text.slice(0, 100)}${result.output_text.length > 100 ? "..." : ""}`);
            console.log(`📊 Category: ${result.category} | Confidence: ${(result.confidence || 0) * 100}%`);
            console.log(`⏱️  Time: ${result.processingTimeMs}ms | Cost: $${result.costUsd?.toFixed(4) || 0}`);
            console.log(`🔧 Tools: ${result.toolsUsed?.join(", ") || "none"}`);
        } catch (error) {
            console.log(`💥 Error: ${error}`);
        }
    }

    console.log("\n" + "=".repeat(80));
}

async function testSystem() {
    console.log("\n🧪 Testing System Components\n");
    console.log("=".repeat(80));

    // Test health check
    console.log("\n📊 Health Check:");
    const health = getAgentHealth();
    console.log(`   Status: ${health.status}`);
    console.log(`   Skills: ${health.skills.length} loaded`);

    // Test memory
    console.log("\n💾 Memory Store:");
    const memory = getMemoryStore();
    const stats = memory.getStats();
    console.log(`   Total conversations: ${stats.totalConversations}`);
    console.log(`   Total messages: ${stats.totalMessages}`);

    // Test cache
    console.log("\n⚡ Cache:");
    const cache = getCache();
    const cacheStats = cache.getStats();
    console.log(`   Keys: ${cacheStats.keys}`);
    console.log(`   Hit rate: ${cacheStats.hitRate}%`);

    // Test metrics
    console.log("\n📈 Metrics:");
    const systemMetrics = metrics.getSystemMetrics();
    console.log(`   Total requests: ${systemMetrics.totalRequests}`);
    console.log(`   Total cost: $${systemMetrics.totalCostUsd.toFixed(4)}`);
    console.log(`   Avg response time: ${systemMetrics.averageResponseTimeMs}ms`);
    console.log(`   Error rate: ${systemMetrics.errorRate.toFixed(2)}%`);

    console.log("\n" + "=".repeat(80));
}

async function main() {
    console.log(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   Maria V2 - Test Suite                                    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
`);

    try {
        // Run tests
        const classificationResults = await testClassification();
        await testWorkflow();
        await testSystem();

        // Summary
        console.log("\n📋 Test Summary\n");
        console.log("=".repeat(80));
        console.log(`Classification: ${classificationResults.passed}/${classificationResults.total} passed`);
        console.log(`Overall Status: ${classificationResults.failed === 0 ? "✅ All tests passed" : `⚠️  ${classificationResults.failed} tests failed`}`);
        console.log("=".repeat(80));

        // Exit with appropriate code
        process.exit(classificationResults.failed > 0 ? 1 : 0);
    } catch (error) {
        logger.error({ error }, "Test suite failed");
        process.exit(1);
    }
}

main();
