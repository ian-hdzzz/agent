// ============================================
// Maria V2 - Metrics and Observability
// ============================================

import { logger } from "./logger.js";
import type { CategoryCode } from "../types.js";

interface ConversationMetric {
    conversationId: string;
    startTime: number;
    messageCount: number;
    toolsUsed: Set<string>;
    totalCostUsd: number;
    classification?: CategoryCode;
    errors: string[];
    handoffOccurred: boolean;
}

class MetricsCollector {
    private conversations: Map<string, ConversationMetric> = new Map();
    private totalRequests: number = 0;
    private totalErrors: number = 0;
    private classificationDistribution: Map<CategoryCode, number> = new Map();
    private toolUsage: Map<string, number> = new Map();
    private responseTimes: number[] = [];

    startConversation(conversationId: string): ConversationMetric {
        const metric: ConversationMetric = {
            conversationId,
            startTime: Date.now(),
            messageCount: 0,
            toolsUsed: new Set(),
            totalCostUsd: 0,
            errors: [],
            handoffOccurred: false
        };
        this.conversations.set(conversationId, metric);
        this.totalRequests++;
        return metric;
    }

    recordMessage(
        conversationId: string,
        data: {
            toolsUsed?: string[];
            costUsd?: number;
            classification?: CategoryCode;
            responseTimeMs?: number;
            error?: string;
        }
    ) {
        let metric = this.conversations.get(conversationId);
        if (!metric) {
            metric = this.startConversation(conversationId);
        }

        metric.messageCount++;

        if (data.toolsUsed) {
            for (const tool of data.toolsUsed) {
                metric.toolsUsed.add(tool);
                this.toolUsage.set(tool, (this.toolUsage.get(tool) || 0) + 1);
            }
        }

        if (data.costUsd) {
            metric.totalCostUsd += data.costUsd;
        }

        if (data.classification) {
            metric.classification = data.classification;
            this.classificationDistribution.set(
                data.classification,
                (this.classificationDistribution.get(data.classification) || 0) + 1
            );
        }

        if (data.responseTimeMs) {
            this.responseTimes.push(data.responseTimeMs);
            // Keep only last 1000 response times
            if (this.responseTimes.length > 1000) {
                this.responseTimes.shift();
            }
        }

        if (data.error) {
            metric.errors.push(data.error);
            this.totalErrors++;
        }
    }

    recordHandoff(conversationId: string) {
        const metric = this.conversations.get(conversationId);
        if (metric) {
            metric.handoffOccurred = true;
        }
    }

    getConversationMetrics(conversationId: string): ConversationMetric | null {
        return this.conversations.get(conversationId) || null;
    }

    getSystemMetrics() {
        const avgResponseTime = this.responseTimes.length > 0
            ? this.responseTimes.reduce((a, b) => a + b, 0) / this.responseTimes.length
            : 0;

        const totalCost = Array.from(this.conversations.values())
            .reduce((sum, m) => sum + m.totalCostUsd, 0);

        return {
            totalConversations: this.conversations.size,
            totalRequests: this.totalRequests,
            totalErrors: this.totalErrors,
            errorRate: this.totalRequests > 0
                ? (this.totalErrors / this.totalRequests) * 100
                : 0,
            totalCostUsd: totalCost,
            averageResponseTimeMs: Math.round(avgResponseTime),
            classificationDistribution: Object.fromEntries(this.classificationDistribution),
            toolUsage: Object.fromEntries(this.toolUsage)
        };
    }

    getHealthStatus(): {
        status: "healthy" | "degraded" | "unhealthy";
        checks: Record<string, boolean>;
    } {
        const errorRate = this.totalRequests > 0
            ? (this.totalErrors / this.totalRequests)
            : 0;

        const checks = {
            errorRateAcceptable: errorRate < 0.1, // Less than 10% errors
            responseTimeAcceptable: this.responseTimes.length === 0 ||
                (this.responseTimes.reduce((a, b) => a + b, 0) / this.responseTimes.length) < 10000 // Less than 10s avg
        };

        const allHealthy = Object.values(checks).every(v => v);
        const anyHealthy = Object.values(checks).some(v => v);

        return {
            status: allHealthy ? "healthy" : anyHealthy ? "degraded" : "unhealthy",
            checks
        };
    }

    reset() {
        this.conversations.clear();
        this.totalRequests = 0;
        this.totalErrors = 0;
        this.classificationDistribution.clear();
        this.toolUsage.clear();
        this.responseTimes = [];
        logger.info("Metrics reset");
    }
}

// Singleton instance
export const metrics = new MetricsCollector();

/**
 * Performance decorator/measurement helper
 */
export async function measurePerformance<T>(
    operation: string,
    fn: () => Promise<T>
): Promise<{ result: T; durationMs: number }> {
    const start = performance.now();
    try {
        const result = await fn();
        const durationMs = Math.round(performance.now() - start);
        logger.debug({ operation, durationMs }, "Operation completed");
        return { result, durationMs };
    } catch (error) {
        const durationMs = Math.round(performance.now() - start);
        logger.error({ operation, durationMs, error }, "Operation failed");
        throw error;
    }
}
