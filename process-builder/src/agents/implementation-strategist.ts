/**
 * Implementation Strategist Agent
 *
 * Takes optimized process + compliance report → produces implementation plan
 * with change management, training, budget, and PACO agent recommendation.
 * Extended thinking enabled (budget: 10000).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, ImplementationPlan } from "../types.js";
import { IMPLEMENTATION_STRATEGIST_PROMPT } from "../prompts/implementation-strategist.js";

interface StrategistInput {
  processName: string;
  department: string;
  asIsAnalysis: string;
  optimizedProcess: string;
  complianceReport?: string;
}

export class ImplementationStrategistAgent extends BaseAgent<ImplementationPlan> {
  readonly name = "Implementation Strategist";
  readonly thinkingBudget = 10000;

  constructor(client: Anthropic, config: AgentConfig) {
    super(client, config);
  }

  protected getSystemPrompt(): string {
    return IMPLEMENTATION_STRATEGIST_PROMPT;
  }

  protected buildUserContent(
    input: StrategistInput
  ): Anthropic.Messages.ContentBlockParam[] {
    let text = `NOMBRE DEL TRÁMITE: ${input.processName}\nDEPENDENCIA: ${input.department}\n\n--- ANÁLISIS DEL PROCESO ACTUAL (AS-IS) ---\n\n${input.asIsAnalysis}\n\n--- PROCESO OPTIMIZADO (TO-BE) ---\n\n${input.optimizedProcess}`;

    if (input.complianceReport) {
      text += `\n\n--- AUDITORÍA DE CUMPLIMIENTO REGULATORIO ---\n\n${input.complianceReport}`;
    }

    return [{ type: "text", text }];
  }

  protected getMaxTokens(): number {
    return 16000;
  }
}
