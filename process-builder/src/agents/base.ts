/**
 * BaseAgent — Abstract base class for all pipeline agents.
 *
 * Provides:
 * - Anthropic SDK call with extended thinking support
 * - Retry with exponential backoff (3 attempts)
 * - Rate limit handling (429 → 30s, 529 → 10s)
 * - Token usage & duration tracking
 * - Structured AgentResult<T> return
 */

import Anthropic from "@anthropic-ai/sdk";
import type {
  AgentResult,
  AgentConfig,
  AgentMetrics,
  TokenUsage,
} from "../types.js";

const MAX_RETRIES = 3;
const RETRY_DELAYS = [1000, 2000, 4000]; // ms
const RATE_LIMIT_WAIT = 30_000; // 429
const OVERLOAD_WAIT = 10_000; // 529

export abstract class BaseAgent<T> {
  protected client: Anthropic;
  protected config: AgentConfig;
  abstract readonly name: string;
  abstract readonly thinkingBudget: number;

  constructor(client: Anthropic, config: AgentConfig) {
    this.client = client;
    this.config = config;
  }

  /**
   * Subclasses implement this to define the system prompt.
   */
  protected abstract getSystemPrompt(): string;

  /**
   * Subclasses implement this to build the user message content.
   */
  protected abstract buildUserContent(
    input: any
  ): Anthropic.Messages.ContentBlockParam[];

  /**
   * Subclasses implement this to parse the text response into typed data.
   * Default: returns the text as-is (for markdown-output agents).
   */
  protected parseResponse(text: string): T {
    return text as unknown as T;
  }

  /**
   * Max tokens for the response (override per agent if needed).
   */
  protected getMaxTokens(): number {
    return 16000;
  }

  /**
   * Run the agent with retry, tracking, and structured result.
   */
  async run(input: any): Promise<AgentResult<T>> {
    const startTime = Date.now();
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const { text, tokenUsage } = await this.callModel(input);
        const data = this.parseResponse(text);
        const durationMs = Date.now() - startTime;

        return {
          success: true,
          data,
          markdownOutput: text,
          metrics: this.buildMetrics(tokenUsage, durationMs),
        };
      } catch (err: any) {
        lastError = err;

        // Rate limit: wait longer
        if (err?.status === 429) {
          await sleep(RATE_LIMIT_WAIT);
          continue;
        }

        // Overload: wait shorter
        if (err?.status === 529) {
          await sleep(OVERLOAD_WAIT);
          continue;
        }

        // Other errors: exponential backoff
        if (attempt < MAX_RETRIES - 1) {
          await sleep(RETRY_DELAYS[attempt]);
        }
      }
    }

    const durationMs = Date.now() - startTime;
    return {
      success: false,
      data: "" as unknown as T,
      markdownOutput: "",
      metrics: this.buildMetrics(emptyTokenUsage(), durationMs),
      error: lastError?.message || "Unknown error after retries",
    };
  }

  private async callModel(
    input: any
  ): Promise<{ text: string; tokenUsage: TokenUsage }> {
    const systemPrompt = this.getSystemPrompt();
    const userContent = this.buildUserContent(input);
    const maxTokens = this.getMaxTokens();
    const useThinking =
      this.config.thinkingEnabled && this.thinkingBudget > 0;

    const params: Anthropic.Messages.MessageCreateParams = {
      model: this.config.model,
      max_tokens: useThinking ? maxTokens + this.thinkingBudget : maxTokens,
      system: systemPrompt,
      messages: [{ role: "user", content: userContent }],
      ...(useThinking
        ? {
            thinking: {
              type: "enabled" as const,
              budget_tokens: this.thinkingBudget,
            },
          }
        : {}),
    };

    const response = await this.client.messages.create(params);

    // Extract text from response (skip thinking blocks)
    let text = "";
    for (const block of response.content) {
      if (block.type === "text") {
        text += block.text;
      }
    }

    if (!text) {
      throw new Error(`${this.name}: No text content in response`);
    }

    const tokenUsage: TokenUsage = {
      inputTokens: response.usage?.input_tokens ?? 0,
      outputTokens: response.usage?.output_tokens ?? 0,
      thinkingTokens:
        (response.usage as any)?.thinking_tokens ??
        (response.usage as any)?.cache_creation_input_tokens ??
        0,
      cacheReadTokens: (response.usage as any)?.cache_read_input_tokens ?? 0,
      cacheCreationTokens:
        (response.usage as any)?.cache_creation_input_tokens ?? 0,
    };

    return { text, tokenUsage };
  }

  private buildMetrics(
    tokenUsage: TokenUsage,
    durationMs: number
  ): AgentMetrics {
    return {
      agentName: this.name,
      model: this.config.model,
      durationMs,
      tokenUsage,
      thinkingEnabled:
        this.config.thinkingEnabled && this.thinkingBudget > 0,
      thinkingBudget: this.thinkingBudget,
    };
  }
}

function emptyTokenUsage(): TokenUsage {
  return {
    inputTokens: 0,
    outputTokens: 0,
    thinkingTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
