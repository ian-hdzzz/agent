/**
 * Diagram Generator Agent
 *
 * Reusable agent for generating Mermaid.js diagrams.
 * Wraps the existing AS-IS and TO-BE diagram prompts.
 * No extended thinking (diagram generation is more mechanical).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, DiagramOutput } from "../types.js";
import {
  DIAGRAM_AS_IS_PROMPT,
  DIAGRAM_TO_BE_PROMPT,
} from "../prompts/diagram-generator.js";

type DiagramType = "as-is" | "to-be-digital" | "to-be-hybrid";

interface DiagramInput {
  sourceMarkdown: string;
  diagramType: DiagramType;
  processName?: string;
}

export class DiagramGeneratorAgent extends BaseAgent<DiagramOutput> {
  readonly name: string;
  readonly thinkingBudget = 0; // No thinking for diagrams
  private diagramType: DiagramType;

  constructor(
    client: Anthropic,
    config: AgentConfig,
    diagramType: DiagramType
  ) {
    super(client, config);
    this.diagramType = diagramType;
    this.name = `Diagram Generator (${diagramType})`;
  }

  protected getSystemPrompt(): string {
    if (this.diagramType === "as-is") {
      return DIAGRAM_AS_IS_PROMPT;
    }
    // Both TO-BE variants use the TO-BE prompt with different instructions
    return DIAGRAM_TO_BE_PROMPT;
  }

  protected buildUserContent(
    input: DiagramInput
  ): Anthropic.Messages.ContentBlockParam[] {
    let text = input.sourceMarkdown;

    if (input.diagramType === "to-be-hybrid") {
      text =
        "INSTRUCCIÓN ESPECIAL: Genera el diagrama para el ESCENARIO HÍBRIDO/PAPEL del proceso optimizado. " +
        "Este diagrama debe mostrar el flujo donde el ciudadano no cuenta con e.firma o prefiere atención presencial. " +
        "Incluye los componentes tanto digitales (captura por servidor público) como físicos (ventanilla, documentos en papel).\n\n" +
        text;
    }

    return [{ type: "text", text }];
  }

  protected parseResponse(text: string): DiagramOutput {
    return {
      mermaidCode: text,
      diagramType: this.diagramType,
    };
  }

  protected getMaxTokens(): number {
    return 8000;
  }
}
