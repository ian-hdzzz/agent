/**
 * Multi-agent pipeline orchestrator.
 *
 * Stage 1 (sequential):  Document Extractor
 *          ↓
 * Stage 2 (parallel):    Process Analyzer  ║  Compliance Auditor
 *          ↓                                ↓
 * Stage 3 (parallel):    AS-IS Diagram  ║  Process Optimizer (needs both Stage 2)
 *          ↓                               ↓
 * Stage 4 (parallel):    TO-BE Diagram (digital)  ║  TO-BE Diagram (hybrid)  ║  Implementation Strategist
 *          ↓
 * Stage 5 (no LLM):     Executive Summary + Index + metadata.json
 */

import Anthropic from "@anthropic-ai/sdk";
import { resolve } from "path";
import {
  readFileForExtraction,
  writeMarkdown,
  writeMetadata,
  writeToSubdir,
  buildOutputDir,
  ensureOutputDir,
} from "./utils/file-io.js";
import { extractMermaidCode, validateMermaid, wrapMermaidBlock } from "./utils/mermaid.js";
import { DocumentExtractorAgent } from "./agents/document-extractor.js";
import { ProcessAnalyzerAgent } from "./agents/process-analyzer.js";
import { ProcessOptimizerAgent } from "./agents/process-optimizer.js";
import { DiagramGeneratorAgent } from "./agents/diagram-generator.js";
import { ComplianceAuditorAgent } from "./agents/compliance-auditor.js";
import { ImplementationStrategistAgent } from "./agents/implementation-strategist.js";
import type {
  PipelineInput,
  PipelineResult,
  PipelineMetadata,
  ProgressCallback,
  AgentConfig,
  AgentMetrics,
  TokenUsage,
  AgentResult,
} from "./types.js";
import { MODEL_MAP } from "./types.js";

// ─── Executive Summary Prompt (lightweight compiler) ─────────────

const EXECUTIVE_SUMMARY_PROMPT = `Eres un consultor senior en transformación digital gubernamental en México.

Tu tarea es generar un RESUMEN EJECUTIVO a partir de los análisis proporcionados de un trámite gubernamental.

REGLAS:
- Output SOLO en español
- Output SOLO en formato markdown
- Sé conciso pero completo
- Enfócate en datos duros: tiempos, costos, pasos eliminados
- Incluye la hoja de ruta de implementación

FORMATO DE SALIDA:

## Resumen Ejecutivo

### Hallazgos Clave
- (3-5 bullet points con los hallazgos más importantes del análisis)

### Métricas de Impacto

| Métrica | Estado Actual | Estado Optimizado | Mejora |
|---------|---------------|-------------------|--------|
| Tiempo total del trámite | X días | Y días | -Z% |
| Visitas presenciales requeridas | X | Y | -Z |
| Pasos del proceso | X | Y | -Z |
| Puntos de decisión manual | X | Y | -Z |
| Nivel de digitalización | X% | Y% | +Z% |

### Inversión y Retorno
- Costo estimado de implementación
- Ahorro anual proyectado
- Período de recuperación

### Hoja de Ruta

#### Fase 1: Quick Wins (0-3 meses)
- (acciones inmediatas de alto impacto y bajo costo)

#### Fase 2: Transformación Media (3-9 meses)
- (cambios estructurales que requieren desarrollo)

#### Fase 3: Transformación Completa (9-18 meses)
- (digitalización completa con integración de sistemas)

### Riesgos Principales
- (top 3 riesgos con mitigación)

### Recomendación
(Párrafo final con la recomendación clara de acción)
`;

// ─── Pipeline ─────────────────────────────────────────────────────

export async function runPipeline(
  input: PipelineInput,
  onProgress?: ProgressCallback
): Promise<PipelineResult> {
  const client = new Anthropic();
  const model = MODEL_MAP[input.model];
  const agentConfig: AgentConfig = {
    model,
    thinkingEnabled: input.thinkingEnabled,
  };

  const outputDir = buildOutputDir(input.outputBaseDir, input.processName);
  ensureOutputDir(outputDir);

  const progress = onProgress || (() => {});
  const files: string[] = [];
  const agentMetrics: AgentMetrics[] = [];
  const skippedAgents: string[] = [];
  const failedAgents: string[] = [];
  const startedAt = new Date().toISOString();
  const pipelineStart = Date.now();

  const header = `# Proceso: ${input.processName}\n**Dependencia:** ${input.department}\n**Fecha de análisis:** ${new Date().toISOString().slice(0, 10)}\n**Modelo:** ${model}\n\n---\n\n`;

  // ═══════════════════════════════════════════════════════════════
  // STAGE 1: Document Extraction (sequential)
  // ═══════════════════════════════════════════════════════════════
  progress("Extracción de documentos", "start");

  let processText: string;
  const sourceFiles: string[] = [];

  if (input.inputFiles.length === 1) {
    const file = readFileForExtraction(resolve(input.inputFiles[0]));
    sourceFiles.push(file.filename);

    if (file.mimeType.startsWith("text/")) {
      // Skip LLM extraction for plain text files
      processText = file.content;
      progress("Extracción de documentos", "done", "Texto directo");
    } else {
      // Use LLM to extract content from PDF/image
      const extractor = new DocumentExtractorAgent(client, agentConfig);
      const result = await extractor.run({ files: [file] });
      agentMetrics.push(result.metrics);

      if (!result.success) {
        throw new Error(`Extracción fallida: ${result.error}`);
      }
      processText = result.data.combinedText;
      progress("Extracción de documentos", "done");
    }
  } else {
    // Multiple files — always use extractor
    const extractedFiles = input.inputFiles.map((f) =>
      readFileForExtraction(resolve(f))
    );
    sourceFiles.push(...extractedFiles.map((f) => f.filename));

    // Check if all are text files
    const allText = extractedFiles.every((f) => f.mimeType.startsWith("text/"));

    if (allText) {
      processText = extractedFiles
        .map((f) => `--- ${f.filename} ---\n\n${f.content}`)
        .join("\n\n");
      progress("Extracción de documentos", "done", "Textos combinados");
    } else {
      const extractor = new DocumentExtractorAgent(client, agentConfig);
      const result = await extractor.run({ files: extractedFiles });
      agentMetrics.push(result.metrics);

      if (!result.success) {
        throw new Error(`Extracción fallida: ${result.error}`);
      }
      processText = result.data.combinedText;
      progress("Extracción de documentos", "done");
    }
  }

  // Write extraction output
  files.push(
    writeMarkdown(
      outputDir,
      "01-extraccion.md",
      header +
        `## Contenido Extraído\n\n**Archivos fuente:** ${sourceFiles.join(", ")}\n\n---\n\n${processText}`
    )
  );

  // ═══════════════════════════════════════════════════════════════
  // STAGE 2: Process Analyzer + Compliance Auditor (parallel)
  // ═══════════════════════════════════════════════════════════════
  const stage2Tasks: Array<{ name: string; promise: Promise<AgentResult<any>>; fatal: boolean }> = [];

  // Process Analyzer (FATAL)
  progress("Análisis del proceso actual (AS-IS)", "start");
  const analyzer = new ProcessAnalyzerAgent(client, agentConfig);
  stage2Tasks.push({
    name: "Process Analyzer",
    promise: analyzer.run({
      processName: input.processName,
      department: input.department,
      processText,
    }),
    fatal: true,
  });

  // Compliance Auditor (NON-FATAL)
  if (!input.skipCompliance) {
    progress("Auditoría de cumplimiento regulatorio", "start");
    const auditor = new ComplianceAuditorAgent(client, agentConfig);
    stage2Tasks.push({
      name: "Compliance Auditor",
      promise: auditor.run({
        processName: input.processName,
        department: input.department,
        processText,
      }),
      fatal: false,
    });
  } else {
    skippedAgents.push("Compliance Auditor");
  }

  const stage2Results = await Promise.allSettled(
    stage2Tasks.map((t) => t.promise)
  );

  // Process Stage 2 results
  let asIsAnalysis = "";
  let complianceReport = "";

  for (let i = 0; i < stage2Tasks.length; i++) {
    const task = stage2Tasks[i];
    const result = stage2Results[i];

    if (result.status === "fulfilled") {
      agentMetrics.push(result.value.metrics);
      if (result.value.success) {
        if (task.name === "Process Analyzer") {
          asIsAnalysis = result.value.markdownOutput;
          progress("Análisis del proceso actual (AS-IS)", "done");
        } else {
          complianceReport = result.value.markdownOutput;
          progress("Auditoría de cumplimiento regulatorio", "done");
        }
      } else if (task.fatal) {
        throw new Error(`${task.name} falló: ${result.value.error}`);
      } else {
        failedAgents.push(task.name);
        progress("Auditoría de cumplimiento regulatorio", "warn", result.value.error || "Error desconocido");
      }
    } else {
      if (task.fatal) {
        throw new Error(`${task.name} falló: ${result.reason?.message || "Error desconocido"}`);
      }
      failedAgents.push(task.name);
      progress("Auditoría de cumplimiento regulatorio", "warn", result.reason?.message || "Error");
    }
  }

  // Write AS-IS analysis
  files.push(
    writeMarkdown(outputDir, "02-proceso-actual.md", header + asIsAnalysis)
  );

  // Write compliance report (if available)
  if (complianceReport) {
    files.push(
      writeMarkdown(
        outputDir,
        "03-auditoria-cumplimiento.md",
        header + complianceReport
      )
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // STAGE 3: AS-IS Diagram + Process Optimizer (parallel)
  // ═══════════════════════════════════════════════════════════════
  const stage3Tasks: Array<{ name: string; promise: Promise<AgentResult<any>>; fatal: boolean; type: string }> = [];

  // AS-IS Diagram (NON-FATAL)
  progress("Diagrama del proceso actual (AS-IS)", "start");
  const asIsDiagramAgent = new DiagramGeneratorAgent(client, agentConfig, "as-is");
  stage3Tasks.push({
    name: "AS-IS Diagram",
    promise: asIsDiagramAgent.run({
      sourceMarkdown: asIsAnalysis || processText,
      diagramType: "as-is",
      processName: input.processName,
    }),
    fatal: false,
    type: "as-is-diagram",
  });

  // Process Optimizer (FATAL)
  progress("Optimización del proceso (TO-BE)", "start");
  const optimizer = new ProcessOptimizerAgent(client, agentConfig);
  stage3Tasks.push({
    name: "Process Optimizer",
    promise: optimizer.run({
      processName: input.processName,
      department: input.department,
      asIsAnalysis,
      originalText: processText,
      complianceReport: complianceReport || undefined,
    }),
    fatal: true,
    type: "optimizer",
  });

  const stage3Results = await Promise.allSettled(
    stage3Tasks.map((t) => t.promise)
  );

  let asIsMermaid = "";
  let toBeOptimization = "";

  for (let i = 0; i < stage3Tasks.length; i++) {
    const task = stage3Tasks[i];
    const result = stage3Results[i];

    if (result.status === "fulfilled") {
      agentMetrics.push(result.value.metrics);
      if (result.value.success) {
        if (task.type === "as-is-diagram") {
          try {
            asIsMermaid = extractMermaidCode(result.value.markdownOutput);
            const validation = validateMermaid(asIsMermaid);
            if (!validation.valid) {
              progress("Diagrama del proceso actual (AS-IS)", "warn", `Advertencias: ${validation.errors.join("; ")}`);
            }
          } catch {
            asIsMermaid = 'graph TD\n  A["Error generando diagrama"] --> B["Revisar manualmente"]';
            progress("Diagrama del proceso actual (AS-IS)", "warn", "No se pudo extraer el diagrama");
          }
          progress("Diagrama del proceso actual (AS-IS)", "done");
        } else {
          toBeOptimization = result.value.markdownOutput;
          progress("Optimización del proceso (TO-BE)", "done");
        }
      } else if (task.fatal) {
        throw new Error(`${task.name} falló: ${result.value.error}`);
      } else {
        failedAgents.push(task.name);
        progress("Diagrama del proceso actual (AS-IS)", "warn", result.value.error || "Error");
      }
    } else {
      if (task.fatal) {
        throw new Error(`${task.name} falló: ${result.reason?.message || "Error"}`);
      }
      failedAgents.push(task.name);
      progress("Diagrama del proceso actual (AS-IS)", "warn", result.reason?.message || "Error");
    }
  }

  // Embed AS-IS diagram in the analysis file
  if (asIsMermaid) {
    const asIsWithDiagram =
      header +
      asIsAnalysis +
      "\n\n---\n\n## Diagrama del Proceso Actual\n\n" +
      wrapMermaidBlock(asIsMermaid);
    writeMarkdown(outputDir, "02-proceso-actual.md", asIsWithDiagram);
    files.push(writeToSubdir(outputDir, "diagramas", "as-is.mmd", asIsMermaid));
  }

  // Write TO-BE optimization
  files.push(
    writeMarkdown(outputDir, "04-proceso-optimizado.md", header + toBeOptimization)
  );

  // ═══════════════════════════════════════════════════════════════
  // STAGE 4: TO-BE Diagrams + Implementation Strategist (parallel)
  // ═══════════════════════════════════════════════════════════════
  const stage4Tasks: Array<{ name: string; promise: Promise<AgentResult<any>>; fatal: boolean; type: string }> = [];

  // TO-BE Digital Diagram (NON-FATAL)
  progress("Diagrama TO-BE (digital)", "start");
  const toBeDigitalAgent = new DiagramGeneratorAgent(client, agentConfig, "to-be-digital");
  stage4Tasks.push({
    name: "TO-BE Digital Diagram",
    promise: toBeDigitalAgent.run({
      sourceMarkdown: toBeOptimization,
      diagramType: "to-be-digital",
      processName: input.processName,
    }),
    fatal: false,
    type: "to-be-digital",
  });

  // TO-BE Hybrid Diagram (NON-FATAL)
  progress("Diagrama TO-BE (híbrido)", "start");
  const toBeHybridAgent = new DiagramGeneratorAgent(client, agentConfig, "to-be-hybrid");
  stage4Tasks.push({
    name: "TO-BE Hybrid Diagram",
    promise: toBeHybridAgent.run({
      sourceMarkdown: toBeOptimization,
      diagramType: "to-be-hybrid",
      processName: input.processName,
    }),
    fatal: false,
    type: "to-be-hybrid",
  });

  // Implementation Strategist (NON-FATAL)
  if (!input.skipImplementation) {
    progress("Plan de implementación", "start");
    const strategist = new ImplementationStrategistAgent(client, agentConfig);
    stage4Tasks.push({
      name: "Implementation Strategist",
      promise: strategist.run({
        processName: input.processName,
        department: input.department,
        asIsAnalysis,
        optimizedProcess: toBeOptimization,
        complianceReport: complianceReport || undefined,
      }),
      fatal: false,
      type: "strategist",
    });
  } else {
    skippedAgents.push("Implementation Strategist");
  }

  const stage4Results = await Promise.allSettled(
    stage4Tasks.map((t) => t.promise)
  );

  let toBeDigitalMermaid = "";
  let toBeHybridMermaid = "";
  let implementationPlan = "";

  for (let i = 0; i < stage4Tasks.length; i++) {
    const task = stage4Tasks[i];
    const result = stage4Results[i];

    if (result.status === "fulfilled") {
      agentMetrics.push(result.value.metrics);
      if (result.value.success) {
        if (task.type === "to-be-digital") {
          try {
            toBeDigitalMermaid = extractMermaidCode(result.value.markdownOutput);
            const validation = validateMermaid(toBeDigitalMermaid);
            if (!validation.valid) {
              progress("Diagrama TO-BE (digital)", "warn", `Advertencias: ${validation.errors.join("; ")}`);
            }
          } catch {
            toBeDigitalMermaid = 'graph TD\n  A["Error generando diagrama"] --> B["Revisar manualmente"]';
            progress("Diagrama TO-BE (digital)", "warn", "No se pudo extraer");
          }
          progress("Diagrama TO-BE (digital)", "done");
        } else if (task.type === "to-be-hybrid") {
          try {
            toBeHybridMermaid = extractMermaidCode(result.value.markdownOutput);
            const validation = validateMermaid(toBeHybridMermaid);
            if (!validation.valid) {
              progress("Diagrama TO-BE (híbrido)", "warn", `Advertencias: ${validation.errors.join("; ")}`);
            }
          } catch {
            toBeHybridMermaid = 'graph TD\n  A["Error generando diagrama"] --> B["Revisar manualmente"]';
            progress("Diagrama TO-BE (híbrido)", "warn", "No se pudo extraer");
          }
          progress("Diagrama TO-BE (híbrido)", "done");
        } else {
          implementationPlan = result.value.markdownOutput;
          progress("Plan de implementación", "done");
        }
      } else {
        failedAgents.push(task.name);
        const label = task.type === "to-be-digital" ? "Diagrama TO-BE (digital)"
          : task.type === "to-be-hybrid" ? "Diagrama TO-BE (híbrido)"
          : "Plan de implementación";
        progress(label, "warn", result.value.error || "Error");
      }
    } else {
      failedAgents.push(task.name);
      const label = task.type === "to-be-digital" ? "Diagrama TO-BE (digital)"
        : task.type === "to-be-hybrid" ? "Diagrama TO-BE (híbrido)"
        : "Plan de implementación";
      progress(label, "warn", result.reason?.message || "Error");
    }
  }

  // Embed TO-BE diagrams in optimization file
  if (toBeDigitalMermaid || toBeHybridMermaid) {
    let optimizedContent = header + toBeOptimization;
    if (toBeDigitalMermaid) {
      optimizedContent +=
        "\n\n---\n\n## Diagrama del Proceso Optimizado (Digital)\n\n" +
        wrapMermaidBlock(toBeDigitalMermaid);
      files.push(
        writeToSubdir(outputDir, "diagramas", "to-be-digital.mmd", toBeDigitalMermaid)
      );
    }
    if (toBeHybridMermaid) {
      optimizedContent +=
        "\n\n---\n\n## Diagrama del Proceso Optimizado (Híbrido)\n\n" +
        wrapMermaidBlock(toBeHybridMermaid);
      files.push(
        writeToSubdir(outputDir, "diagramas", "to-be-hibrido.mmd", toBeHybridMermaid)
      );
    }
    writeMarkdown(outputDir, "04-proceso-optimizado.md", optimizedContent);
  }

  // Write implementation plan
  if (implementationPlan) {
    files.push(
      writeMarkdown(
        outputDir,
        "05-plan-implementacion.md",
        header + implementationPlan
      )
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // STAGE 5: Executive Summary + Index + Metadata (no LLM for index/metadata)
  // ═══════════════════════════════════════════════════════════════
  progress("Compilando resumen ejecutivo", "start");

  // Executive summary via LLM
  const summaryClient = new Anthropic();
  let executiveSummary = "";
  try {
    let summaryInput = `NOMBRE: ${input.processName}\nDEPENDENCIA: ${input.department}\n\n--- ANÁLISIS AS-IS ---\n${asIsAnalysis}\n\n--- OPTIMIZACIÓN TO-BE ---\n${toBeOptimization}`;
    if (complianceReport) {
      summaryInput += `\n\n--- AUDITORÍA DE CUMPLIMIENTO ---\n${complianceReport}`;
    }
    if (implementationPlan) {
      summaryInput += `\n\n--- PLAN DE IMPLEMENTACIÓN ---\n${implementationPlan}`;
    }

    const summaryResponse = await summaryClient.messages.create({
      model,
      max_tokens: 8000,
      system: EXECUTIVE_SUMMARY_PROMPT,
      messages: [{ role: "user", content: summaryInput }],
    });

    const block = summaryResponse.content[0];
    if (block.type === "text") {
      executiveSummary = block.text;
    }

    agentMetrics.push({
      agentName: "Executive Summary",
      model,
      durationMs: 0,
      tokenUsage: {
        inputTokens: summaryResponse.usage?.input_tokens ?? 0,
        outputTokens: summaryResponse.usage?.output_tokens ?? 0,
        thinkingTokens: 0,
        cacheReadTokens: 0,
        cacheCreationTokens: 0,
      },
      thinkingEnabled: false,
      thinkingBudget: 0,
    });
  } catch (err: any) {
    executiveSummary = `## Resumen Ejecutivo\n\n*Error generando resumen ejecutivo: ${err.message}*`;
    progress("Compilando resumen ejecutivo", "warn", err.message);
  }

  files.push(
    writeMarkdown(outputDir, "00-resumen-ejecutivo.md", header + executiveSummary)
  );
  progress("Compilando resumen ejecutivo", "done");

  // Build metadata
  const totalDurationMs = Date.now() - pipelineStart;
  const totalTokens = agentMetrics.reduce<TokenUsage>(
    (acc, m) => ({
      inputTokens: acc.inputTokens + m.tokenUsage.inputTokens,
      outputTokens: acc.outputTokens + m.tokenUsage.outputTokens,
      thinkingTokens: acc.thinkingTokens + m.tokenUsage.thinkingTokens,
      cacheReadTokens: acc.cacheReadTokens + m.tokenUsage.cacheReadTokens,
      cacheCreationTokens: acc.cacheCreationTokens + m.tokenUsage.cacheCreationTokens,
    }),
    { inputTokens: 0, outputTokens: 0, thinkingTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0 }
  );

  const metadata: PipelineMetadata = {
    processName: input.processName,
    department: input.department,
    model,
    startedAt,
    completedAt: new Date().toISOString(),
    totalDurationMs,
    agents: agentMetrics,
    totalTokens,
    sourceFiles,
    pipelineVersion: "2.0.0",
    skippedAgents,
    failedAgents,
  };

  files.push(writeMetadata(outputDir, metadata));

  // Write README index
  const indexContent = buildIndex(input, metadata, {
    hasCompliance: !!complianceReport,
    hasImplementation: !!implementationPlan,
    hasAsIsDiagram: !!asIsMermaid,
    hasToBeDigital: !!toBeDigitalMermaid,
    hasToBeHybrid: !!toBeHybridMermaid,
  });
  files.push(writeMarkdown(outputDir, "README.md", indexContent));

  // ═══════════════════════════════════════════════════════════════
  // Optional: Push to PACO
  // ═══════════════════════════════════════════════════════════════
  if (input.pushToPaco && input.pacoUrl && input.pacoToken) {
    progress("Enviando a PACO", "start");
    try {
      await pushToPaco(input.pacoUrl, input.pacoToken, {
        name: input.processName,
        department: input.department,
        extraction_md: processText,
        as_is_analysis_md: asIsAnalysis,
        compliance_audit_md: complianceReport || null,
        to_be_optimization_md: toBeOptimization,
        implementation_plan_md: implementationPlan || null,
        executive_summary_md: executiveSummary,
        diagram_as_is: asIsMermaid || null,
        diagram_to_be_digital: toBeDigitalMermaid || null,
        diagram_to_be_hybrid: toBeHybridMermaid || null,
        run_metadata: metadata,
        model_used: model,
        source_files: sourceFiles,
        tags: [],
        status: "completed",
      });
      progress("Enviando a PACO", "done");
    } catch (err: any) {
      progress("Enviando a PACO", "warn", err.message);
    }
  }

  return { outputDir, files, metadata };
}

// ─── PACO Push ────────────────────────────────────────────────────

async function pushToPaco(
  baseUrl: string,
  token: string,
  data: Record<string, any>
): Promise<void> {
  const url = `${baseUrl.replace(/\/$/, "")}/api/processes`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`PACO API error ${response.status}: ${text}`);
  }
}

// ─── Index Builder ────────────────────────────────────────────────

function buildIndex(
  input: PipelineInput,
  metadata: PipelineMetadata,
  flags: {
    hasCompliance: boolean;
    hasImplementation: boolean;
    hasAsIsDiagram: boolean;
    hasToBeDigital: boolean;
    hasToBeHybrid: boolean;
  }
): string {
  const date = new Date().toISOString().slice(0, 10);
  const durationSec = (metadata.totalDurationMs / 1000).toFixed(1);
  const totalTokensCount =
    metadata.totalTokens.inputTokens + metadata.totalTokens.outputTokens;

  let index = `# ${input.processName}

**Dependencia:** ${input.department}
**Fecha de análisis:** ${date}
**Modelo:** ${metadata.model}
**Duración total:** ${durationSec}s
**Tokens totales:** ${totalTokensCount.toLocaleString()}

---

## Contenido del Análisis

| # | Archivo | Descripción |
|---|---------|-------------|
| 0 | [00-resumen-ejecutivo.md](./00-resumen-ejecutivo.md) | Resumen ejecutivo y hoja de ruta |
| 1 | [01-extraccion.md](./01-extraccion.md) | Contenido extraído de archivos fuente |
| 2 | [02-proceso-actual.md](./02-proceso-actual.md) | Análisis completo del proceso actual (AS-IS) |
`;

  if (flags.hasCompliance) {
    index += `| 3 | [03-auditoria-cumplimiento.md](./03-auditoria-cumplimiento.md) | Auditoría de cumplimiento regulatorio |\n`;
  }

  index += `| 4 | [04-proceso-optimizado.md](./04-proceso-optimizado.md) | Proceso optimizado (TO-BE) con diagramas |\n`;

  if (flags.hasImplementation) {
    index += `| 5 | [05-plan-implementacion.md](./05-plan-implementacion.md) | Plan de implementación y gestión del cambio |\n`;
  }

  index += `\n## Diagramas\n\n`;

  if (flags.hasAsIsDiagram) {
    index += `- [AS-IS](./diagramas/as-is.mmd) — Proceso actual\n`;
  }
  if (flags.hasToBeDigital) {
    index += `- [TO-BE Digital](./diagramas/to-be-digital.mmd) — Proceso optimizado (100% digital)\n`;
  }
  if (flags.hasToBeHybrid) {
    index += `- [TO-BE Híbrido](./diagramas/to-be-hibrido.mmd) — Proceso optimizado (ventanilla + digital)\n`;
  }

  if (metadata.failedAgents.length > 0) {
    index += `\n## Agentes con error\n\n`;
    for (const agent of metadata.failedAgents) {
      index += `- ${agent}\n`;
    }
  }

  if (metadata.skippedAgents.length > 0) {
    index += `\n## Agentes omitidos\n\n`;
    for (const agent of metadata.skippedAgents) {
      index += `- ${agent}\n`;
    }
  }

  index += `\n## Uso de recursos por agente\n\n| Agente | Duración | Input Tokens | Output Tokens | Thinking |\n|--------|----------|-------------|---------------|----------|\n`;

  for (const m of metadata.agents) {
    const dur = (m.durationMs / 1000).toFixed(1);
    index += `| ${m.agentName} | ${dur}s | ${m.tokenUsage.inputTokens.toLocaleString()} | ${m.tokenUsage.outputTokens.toLocaleString()} | ${m.thinkingEnabled ? `${m.thinkingBudget} budget` : "disabled"} |\n`;
  }

  index += `\n---\n\n*Generado por Process Builder v2.0 — Herramienta de Transformación Digital*\n*${date}*\n`;

  return index;
}
