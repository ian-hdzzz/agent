/**
 * Process Optimizer Agent (TO-BE)
 *
 * Wraps the existing world-class process optimizer prompt in the BaseAgent class.
 * Extended thinking enabled (budget: 15000).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, OptimizedProcess } from "../types.js";
import { PROCESS_OPTIMIZER_PROMPT } from "../prompts/process-optimizer.js";

interface OptimizerInput {
  processName: string;
  department: string;
  asIsAnalysis: string;
  originalText: string;
  complianceReport?: string;
}

export class ProcessOptimizerAgent extends BaseAgent<OptimizedProcess> {
  readonly name = "Process Optimizer (TO-BE)";
  readonly thinkingBudget = 15000;

  constructor(client: Anthropic, config: AgentConfig) {
    super(client, config);
  }

  protected getSystemPrompt(): string {
    return PROCESS_OPTIMIZER_PROMPT;
  }

  protected buildUserContent(
    input: OptimizerInput
  ): Anthropic.Messages.ContentBlockParam[] {
    let text = `NOMBRE DEL TRÁMITE: ${input.processName}\nDEPENDENCIA: ${input.department}\n\n--- ANÁLISIS DEL PROCESO ACTUAL (AS-IS) ---\n\n${input.asIsAnalysis}\n\n--- DESCRIPCIÓN ORIGINAL ---\n\n${input.originalText}`;

    if (input.complianceReport) {
      text += `\n\n--- AUDITORÍA DE CUMPLIMIENTO REGULATORIO ---\n\n${input.complianceReport}`;
    }

    return [{ type: "text", text }];
  }

  protected getMaxTokens(): number {
    return 16000;
  }
}
