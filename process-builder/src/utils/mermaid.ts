/**
 * Extract mermaid code block from LLM output.
 * Handles both ```mermaid ... ``` and raw mermaid content.
 */
export function extractMermaidCode(output: string): string {
  const fenceMatch = output.match(/```mermaid\s*\n([\s\S]*?)```/);
  if (fenceMatch) {
    return fenceMatch[1].trim();
  }

  // Try unfenced — check if it starts with graph/flowchart
  const trimmed = output.trim();
  if (/^(graph|flowchart)\s+(TD|TB|LR|RL|BT)/i.test(trimmed)) {
    return trimmed;
  }

  throw new Error(
    "No se pudo extraer código Mermaid válido de la respuesta del modelo."
  );
}

/**
 * Basic Mermaid syntax validation.
 * Checks for common issues that cause render failures.
 */
export function validateMermaid(code: string): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Must start with graph or flowchart directive
  if (!/^(graph|flowchart)\s+(TD|TB|LR|RL|BT)/i.test(code.trim())) {
    errors.push("El diagrama debe iniciar con 'graph TD' o 'flowchart TD'");
  }

  // Check for balanced subgraph/end pairs
  const subgraphCount = (code.match(/\bsubgraph\b/g) || []).length;
  const endCount = (code.match(/^\s*end\s*$/gm) || []).length;
  if (subgraphCount !== endCount) {
    errors.push(
      `Subgraphs desbalanceados: ${subgraphCount} subgraph vs ${endCount} end`
    );
  }

  // Check for arrows inside subgraph blocks (common error)
  const lines = code.split("\n");
  let insideSubgraph = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (/^subgraph\b/.test(line)) insideSubgraph = true;
    if (/^\s*end\s*$/.test(line)) insideSubgraph = false;
    if (insideSubgraph && /-->/.test(line) && !/^subgraph/.test(line)) {
      // Allow node declarations that contain --> in labels
      if (!/\[".*-->.*"\]/.test(line)) {
        errors.push(
          `Línea ${i + 1}: Conexión '-->' dentro de un subgraph (debe estar fuera)`
        );
      }
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Wrap mermaid code in a markdown fenced block for embedding in .md files
 */
export function wrapMermaidBlock(code: string): string {
  return `\`\`\`mermaid\n${code}\n\`\`\``;
}
