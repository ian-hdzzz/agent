"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-foreground mb-4 mt-6 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold text-foreground mb-3 mt-5">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold text-foreground mb-2 mt-4">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-medium text-foreground mb-2 mt-3">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-sm text-foreground-muted mb-3 leading-relaxed">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside text-sm text-foreground-muted mb-3 space-y-1 ml-2">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside text-sm text-foreground-muted mb-3 space-y-1 ml-2">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-foreground-muted">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-coral-500/50 pl-4 py-1 my-3 text-sm text-foreground-muted italic">
              {children}
            </blockquote>
          ),
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code className="bg-background-tertiary text-coral-500 px-1.5 py-0.5 rounded text-xs font-mono">
                  {children}
                </code>
              );
            }
            return (
              <code className="block bg-background text-foreground-muted p-4 rounded-lg text-xs font-mono overflow-x-auto mb-3">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="bg-background rounded-lg overflow-x-auto mb-3">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-3 rounded-lg border border-border">
              <table className="w-full text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-background-tertiary">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 text-left text-xs font-medium text-foreground uppercase tracking-wider border-b border-border">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 text-sm text-foreground-muted border-b border-border">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-background-tertiary/50 transition-colors">
              {children}
            </tr>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-coral-500 hover:text-coral-400 underline underline-offset-2"
            >
              {children}
            </a>
          ),
          hr: () => <hr className="border-border my-4" />,
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-foreground-muted">{children}</em>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
