/**
 * Type definitions for the Process Builder multi-agent pipeline.
 */

// ─── Model Selection ─────────────────────────────────────────────

export type ModelAlias = "sonnet" | "opus" | "haiku";

export const MODEL_MAP: Record<ModelAlias, string> = {
  sonnet: "claude-sonnet-4-5-20250929",
  opus: "claude-opus-4-6",
  haiku: "claude-haiku-4-5-20251001",
};

// ─── Token & Cost Tracking ───────────────────────────────────────

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  thinkingTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
}

export interface AgentMetrics {
  agentName: string;
  model: string;
  durationMs: number;
  tokenUsage: TokenUsage;
  thinkingEnabled: boolean;
  thinkingBudget: number;
}

// ─── Agent Results ───────────────────────────────────────────────

export interface AgentResult<T> {
  success: boolean;
  data: T;
  markdownOutput: string;
  metrics: AgentMetrics;
  error?: string;
}

// ─── Agent Configuration ─────────────────────────────────────────

export interface AgentConfig {
  model: string;
  thinkingEnabled: boolean;
  maxTokens?: number;
}

// ─── Document Extractor ──────────────────────────────────────────

export interface ExtractedFile {
  filename: string;
  mimeType: string;
  sizeBytes: number;
  content: string;
}

export interface ExtractedContent {
  files: ExtractedFile[];
  combinedText: string;
  sourceDescription: string;
}

// ─── Process Analyzer (AS-IS) ────────────────────────────────────

export type AsIsAnalysis = string; // Full markdown output

// ─── Compliance Auditor ──────────────────────────────────────────

export type ComplianceReport = string; // Full markdown output

// ─── Process Optimizer (TO-BE) ───────────────────────────────────

export type OptimizedProcess = string; // Full markdown output

// ─── Diagram Generator ──────────────────────────────────────────

export interface DiagramOutput {
  mermaidCode: string;
  diagramType: "as-is" | "to-be-digital" | "to-be-hybrid";
}

// ─── Implementation Strategist ───────────────────────────────────

export type ImplementationPlan = string; // Full markdown output

// ─── Pipeline I/O ────────────────────────────────────────────────

export interface PipelineInput {
  inputFiles: string[];
  processName: string;
  department: string;
  outputBaseDir: string;
  model: ModelAlias;
  thinkingEnabled: boolean;
  skipCompliance: boolean;
  skipImplementation: boolean;
  pushToPaco: boolean;
  pacoUrl?: string;
  pacoToken?: string;
}

export interface PipelineResult {
  outputDir: string;
  files: string[];
  metadata: PipelineMetadata;
}

export interface PipelineMetadata {
  processName: string;
  department: string;
  model: string;
  startedAt: string;
  completedAt: string;
  totalDurationMs: number;
  agents: AgentMetrics[];
  totalTokens: TokenUsage;
  sourceFiles: string[];
  pipelineVersion: string;
  skippedAgents: string[];
  failedAgents: string[];
}

// ─── Progress Callback ───────────────────────────────────────────

export interface ProgressCallback {
  (stage: string, status: "start" | "done" | "error" | "warn", detail?: string): void;
}
