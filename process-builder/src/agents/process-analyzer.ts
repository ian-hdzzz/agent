/**
 * Process Analyzer Agent (AS-IS)
 *
 * Wraps the existing world-class process analyzer prompt in the BaseAgent class.
 * Extended thinking enabled (budget: 10000).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, AsIsAnalysis } from "../types.js";
import { PROCESS_ANALYZER_PROMPT } from "../prompts/process-analyzer.js";

interface AnalyzerInput {
  processName: string;
  department: string;
  processText: string;
}

export class ProcessAnalyzerAgent extends BaseAgent<AsIsAnalysis> {
  readonly name = "Process Analyzer (AS-IS)";
  readonly thinkingBudget = 10000;

  constructor(client: Anthropic, config: AgentConfig) {
    super(client, config);
  }

  protected getSystemPrompt(): string {
    return PROCESS_ANALYZER_PROMPT;
  }

  protected buildUserContent(
    input: AnalyzerInput
  ): Anthropic.Messages.ContentBlockParam[] {
    return [
      {
        type: "text",
        text: `NOMBRE DEL TRÁMITE: ${input.processName}\nDEPENDENCIA: ${input.department}\n\n${input.processText}`,
      },
    ];
  }

  protected getMaxTokens(): number {
    return 16000;
  }
}
