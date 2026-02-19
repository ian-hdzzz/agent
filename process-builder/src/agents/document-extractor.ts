/**
 * Document Extractor Agent
 *
 * Reads TXT/PDF/images via Claude Vision and extracts structured text.
 * No extended thinking (simple extraction task).
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseAgent } from "./base.js";
import type { AgentConfig, ExtractedContent, ExtractedFile } from "../types.js";
import { buildContentBlocksForFile } from "../utils/file-io.js";

interface ExtractorInput {
  files: ExtractedFile[];
}

export class DocumentExtractorAgent extends BaseAgent<ExtractedContent> {
  readonly name = "Document Extractor";
  readonly thinkingBudget = 0; // No thinking needed

  constructor(client: Anthropic, config: AgentConfig) {
    super(client, config);
  }

  protected getSystemPrompt(): string {
    return EXTRACTOR_PROMPT;
  }

  protected buildUserContent(
    input: ExtractorInput
  ): Anthropic.Messages.ContentBlockParam[] {
    const blocks: any[] = [];

    blocks.push({
      type: "text",
      text: `Extrae y estructura el contenido de ${input.files.length} archivo(s) fuente que describen un trámite gubernamental.\n\nArchivos:`,
    });

    for (const file of input.files) {
      const fileBlocks = buildContentBlocksForFile(file);
      blocks.push(...fileBlocks);
    }

    blocks.push({
      type: "text",
      text: "\n\nExtrae todo el contenido relevante y preséntalo de forma estructurada en español.",
    });

    return blocks as Anthropic.Messages.ContentBlockParam[];
  }

  protected parseResponse(text: string): ExtractedContent {
    return {
      files: [], // Populated by pipeline from input
      combinedText: text,
      sourceDescription: "",
    };
  }

  protected getMaxTokens(): number {
    return 8000;
  }
}

const EXTRACTOR_PROMPT = `Eres un extractor de documentos especializado en trámites gubernamentales mexicanos.

Tu tarea es recibir uno o más archivos (texto, PDF, imágenes) que describen un trámite o proceso gubernamental, y extraer TODO el contenido relevante en formato de texto estructurado.

REGLAS:
- Output SOLO en español
- Output SOLO en formato markdown
- Preserva TODA la información del documento original sin omitir nada
- Si el archivo es una imagen, describe todo el contenido visible incluyendo texto, tablas, diagramas, sellos, firmas
- Si el archivo es un PDF, extrae todo el texto, tablas, y describe elementos visuales
- Si hay múltiples archivos, combínalos en un solo documento coherente indicando de qué archivo proviene cada sección
- NO interpretes ni optimices el contenido — solo extrae fielmente
- Si hay texto ilegible o ambiguo, indícalo con [ilegible] o [ambiguo: posible lectura X]

FORMATO DE SALIDA:

# Contenido Extraído

## Información del Documento
- Tipo de archivo(s): [lista]
- Contenido principal: [breve descripción]

## Contenido Completo

[Todo el contenido extraído, preservando la estructura original lo mejor posible]

## Observaciones de Extracción
- [Notas sobre calidad del documento, elementos ilegibles, etc.]
`;
