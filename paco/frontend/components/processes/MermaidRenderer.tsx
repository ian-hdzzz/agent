"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Copy, Download, AlertTriangle } from "lucide-react";

interface MermaidRendererProps {
  source: string;
  className?: string;
}

export function MermaidRenderer({ source, className }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function renderDiagram() {
      if (!source || !containerRef.current) return;

      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          themeVariables: {
            primaryColor: "#f97066",
            primaryTextColor: "#e5e7eb",
            primaryBorderColor: "#374151",
            lineColor: "#6b7280",
            secondaryColor: "#1f2937",
            tertiaryColor: "#111827",
          },
        });

        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
        const { svg } = await mermaid.render(id, source);

        if (!cancelled) {
          setSvgContent(svg);
          setError(null);
          if (containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || "Failed to render diagram");
          setSvgContent(null);
        }
      }
    }

    renderDiagram();

    return () => {
      cancelled = true;
    };
  }, [source]);

  const handleCopySource = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(source);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  }, [source]);

  const handleDownloadSvg = useCallback(() => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "diagram.svg";
    a.click();
    URL.revokeObjectURL(url);
  }, [svgContent]);

  if (error) {
    return (
      <div className={`rounded-lg border border-error/30 bg-error/5 p-4 ${className || ""}`}>
        <div className="flex items-center gap-2 text-error text-sm mb-2">
          <AlertTriangle className="w-4 h-4" />
          <span>Error al renderizar diagrama</span>
        </div>
        <pre className="text-xs text-foreground-muted font-mono overflow-x-auto">
          {error}
        </pre>
        <details className="mt-2">
          <summary className="text-xs text-foreground-muted cursor-pointer">
            Ver fuente
          </summary>
          <pre className="mt-2 text-xs text-foreground-muted font-mono bg-background p-3 rounded overflow-x-auto">
            {source}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Toolbar */}
      <div className="flex items-center justify-end gap-2 mb-2">
        <button
          onClick={handleCopySource}
          className="flex items-center gap-1.5 text-xs text-foreground-muted hover:text-foreground px-2 py-1 rounded bg-background-tertiary transition-colors"
        >
          <Copy className="w-3 h-3" />
          {copied ? "Copiado" : "Copiar fuente"}
        </button>
        {svgContent && (
          <button
            onClick={handleDownloadSvg}
            className="flex items-center gap-1.5 text-xs text-foreground-muted hover:text-foreground px-2 py-1 rounded bg-background-tertiary transition-colors"
          >
            <Download className="w-3 h-3" />
            Descargar SVG
          </button>
        )}
      </div>

      {/* Diagram container */}
      <div
        ref={containerRef}
        className="bg-background rounded-lg p-4 overflow-x-auto flex items-center justify-center min-h-[200px]"
      >
        {!svgContent && !error && (
          <div className="animate-spin w-6 h-6 border-2 border-coral-500 border-t-transparent rounded-full" />
        )}
      </div>
    </div>
  );
}
