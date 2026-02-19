/**
 * Compliance Auditor Agent
 *
 * Analyzes the extracted process against the Mexican regulatory framework.
 * Extended thinking enabled (budget: 8000).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, ComplianceReport } from "../types.js";
import { COMPLIANCE_AUDITOR_PROMPT } from "../prompts/compliance-auditor.js";

interface AuditorInput {
  processName: string;
  department: string;
  processText: string;
  asIsAnalysis?: string;
}

export class ComplianceAuditorAgent extends BaseAgent<ComplianceReport> {
  readonly name = "Compliance Auditor";
  readonly thinkingBudget = 8000;

  constructor(client: Anthropic, config: AgentConfig) {
    super(client, config);
  }

  protected getSystemPrompt(): string {
    return COMPLIANCE_AUDITOR_PROMPT;
  }

  protected buildUserContent(
    input: AuditorInput
  ): Anthropic.Messages.ContentBlockParam[] {
    let text = `NOMBRE DEL TRÁMITE: ${input.processName}\nDEPENDENCIA: ${input.department}\n\n--- DESCRIPCIÓN DEL PROCESO ---\n\n${input.processText}`;

    if (input.asIsAnalysis) {
      text += `\n\n--- ANÁLISIS AS-IS ---\n\n${input.asIsAnalysis}`;
    }

    return [{ type: "text", text }];
  }

  protected getMaxTokens(): number {
    return 16000;
  }
}
