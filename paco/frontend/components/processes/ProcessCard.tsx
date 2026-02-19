"use client";

import { useRouter } from "next/navigation";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Building2,
  Cpu,
  Calendar,
} from "lucide-react";
import { Process } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";

interface ProcessCardProps {
  process: Process;
}

function StatusIndicator({ status }: { status: Process["status"] }) {
  switch (status) {
    case "analyzing":
      return (
        <span className="flex items-center gap-1.5 text-xs text-amber-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Analizando
        </span>
      );
    case "completed":
      return (
        <span className="flex items-center gap-1.5 text-xs text-success">
          <CheckCircle className="w-4 h-4" />
          Completado
        </span>
      );
    case "error":
      return (
        <span className="flex items-center gap-1.5 text-xs text-error">
          <XCircle className="w-4 h-4" />
          Error
        </span>
      );
  }
}

export function ProcessCard({ process }: ProcessCardProps) {
  const router = useRouter();

  return (
    <div
      onClick={() => router.push(`/processes/${process.id}`)}
      className="block p-5 rounded-lg bg-background-tertiary hover:bg-border/50 transition-colors cursor-pointer"
    >
      {/* Header: name + status */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-medium text-foreground line-clamp-2">
          {process.name}
        </h3>
        <StatusIndicator status={process.status} />
      </div>

      {/* Description */}
      {process.description && (
        <p className="text-sm text-foreground-muted line-clamp-2 mb-3">
          {process.description}
        </p>
      )}

      {/* Department badge */}
      <div className="flex items-center gap-2 mb-3">
        <span className="inline-flex items-center gap-1.5 text-xs bg-coral-500/10 text-coral-500 px-2 py-0.5 rounded">
          <Building2 className="w-3 h-3" />
          {process.department}
        </span>
      </div>

      {/* Tags */}
      {process.tags && process.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {process.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-background-secondary text-foreground-muted px-2 py-0.5 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer: date + model */}
      <div className="flex items-center gap-3 text-xs text-foreground-muted pt-2 border-t border-border">
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {formatDate(process.created_at)}
        </span>
        {process.model_used && (
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3" />
            {process.model_used}
          </span>
        )}
      </div>
    </div>
  );
}
