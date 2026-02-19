"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  Cpu,
  Calendar,
  CheckCircle,
  XCircle,
  Loader2,
  FileText,
  Scale,
  Rocket,
  GitBranch,
  ClipboardList,
} from "lucide-react";
import { Header } from "@/components/ui/Header";
import { MarkdownRenderer } from "@/components/processes/MarkdownRenderer";
import { MermaidRenderer } from "@/components/processes/MermaidRenderer";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";

const TABS = [
  { key: "resumen", label: "Resumen", icon: ClipboardList },
  { key: "as-is", label: "Proceso Actual (AS-IS)", icon: FileText },
  { key: "to-be", label: "Proceso Optimizado (TO-BE)", icon: Rocket },
  { key: "compliance", label: "Cumplimiento Legal", icon: Scale },
  { key: "plan", label: "Plan de Implementacion", icon: GitBranch },
  { key: "diagrams", label: "Diagramas", icon: GitBranch },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "analyzing":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs bg-amber-400/10 text-amber-400 px-2.5 py-1 rounded-full">
          <Loader2 className="w-3 h-3 animate-spin" />
          Analizando
        </span>
      );
    case "completed":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs bg-success/10 text-success px-2.5 py-1 rounded-full">
          <CheckCircle className="w-3 h-3" />
          Completado
        </span>
      );
    case "error":
      return (
        <span className="inline-flex items-center gap-1.5 text-xs bg-error/10 text-error px-2.5 py-1 rounded-full">
          <XCircle className="w-3 h-3" />
          Error
        </span>
      );
    default:
      return null;
  }
}

function EmptyTab({ message }: { message: string }) {
  return (
    <div className="h-64 flex flex-col items-center justify-center text-foreground-muted">
      <FileText className="w-12 h-12 mb-3 opacity-30" />
      <p>{message}</p>
    </div>
  );
}

export default function ProcessDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabKey>("resumen");

  const id = params.id as string;

  const { data: process, isLoading, error } = useQuery({
    queryKey: ["process", id],
    queryFn: () => api.getProcess(id),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div>
        <Header title="Proceso" description="Cargando..." />
        <div className="h-96 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-coral-500 border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (error || !process) {
    return (
      <div>
        <Header title="Proceso" description="Error" />
        <div className="p-6">
          <div className="card p-8 text-center">
            <XCircle className="w-12 h-12 text-error mx-auto mb-3" />
            <p className="text-foreground-muted">
              No se pudo cargar el proceso
            </p>
            <button
              onClick={() => router.push("/processes")}
              className="btn-primary mt-4 px-4 py-2"
            >
              Volver a Procesos
            </button>
          </div>
        </div>
      </div>
    );
  }

  function renderTabContent() {
    switch (activeTab) {
      case "resumen":
        return process!.executive_summary_md ? (
          <MarkdownRenderer content={process!.executive_summary_md} />
        ) : (
          <EmptyTab message="Resumen ejecutivo no disponible" />
        );

      case "as-is":
        return (
          <div className="space-y-6">
            {process!.as_is_analysis_md ? (
              <MarkdownRenderer content={process!.as_is_analysis_md} />
            ) : (
              <EmptyTab message="Analisis AS-IS no disponible" />
            )}
            {process!.diagram_as_is && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama AS-IS
                </h3>
                <MermaidRenderer source={process!.diagram_as_is} />
              </div>
            )}
          </div>
        );

      case "to-be":
        return (
          <div className="space-y-6">
            {process!.to_be_optimization_md ? (
              <MarkdownRenderer content={process!.to_be_optimization_md} />
            ) : (
              <EmptyTab message="Optimizacion TO-BE no disponible" />
            )}
            {process!.diagram_to_be_digital && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama TO-BE (Digital)
                </h3>
                <MermaidRenderer source={process!.diagram_to_be_digital} />
              </div>
            )}
            {process!.diagram_to_be_hybrid && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama TO-BE (Hibrido)
                </h3>
                <MermaidRenderer source={process!.diagram_to_be_hybrid} />
              </div>
            )}
          </div>
        );

      case "compliance":
        return process!.compliance_audit_md ? (
          <MarkdownRenderer content={process!.compliance_audit_md} />
        ) : (
          <EmptyTab message="Auditoria de cumplimiento no disponible" />
        );

      case "plan":
        return process!.implementation_plan_md ? (
          <MarkdownRenderer content={process!.implementation_plan_md} />
        ) : (
          <EmptyTab message="Plan de implementacion no disponible" />
        );

      case "diagrams":
        return (
          <div className="space-y-8">
            {process!.diagram_as_is && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama AS-IS
                </h3>
                <MermaidRenderer source={process!.diagram_as_is} />
              </div>
            )}
            {process!.diagram_to_be_digital && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama TO-BE (Digital)
                </h3>
                <MermaidRenderer source={process!.diagram_to_be_digital} />
              </div>
            )}
            {process!.diagram_to_be_hybrid && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-3">
                  Diagrama TO-BE (Hibrido)
                </h3>
                <MermaidRenderer source={process!.diagram_to_be_hybrid} />
              </div>
            )}
            {!process!.diagram_as_is &&
              !process!.diagram_to_be_digital &&
              !process!.diagram_to_be_hybrid && (
                <EmptyTab message="No hay diagramas disponibles" />
              )}
          </div>
        );
    }
  }

  return (
    <div>
      <Header title="Proceso" description={process.name} />

      <div className="p-6 space-y-6">
        {/* Back button + process header */}
        <div>
          <button
            onClick={() => router.push("/processes")}
            className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver a Procesos
          </button>

          <div className="card p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h2 className="text-xl font-bold text-foreground mb-2">
                  {process.name}
                </h2>
                {process.description && (
                  <p className="text-sm text-foreground-muted mb-3">
                    {process.description}
                  </p>
                )}
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="inline-flex items-center gap-1.5 text-xs bg-coral-500/10 text-coral-500 px-2 py-0.5 rounded">
                    <Building2 className="w-3 h-3" />
                    {process.department}
                  </span>
                  <StatusBadge status={process.status} />
                  <span className="flex items-center gap-1 text-xs text-foreground-muted">
                    <Calendar className="w-3 h-3" />
                    {formatDate(process.created_at)}
                  </span>
                  {process.model_used && (
                    <span className="flex items-center gap-1 text-xs text-foreground-muted">
                      <Cpu className="w-3 h-3" />
                      {process.model_used}
                    </span>
                  )}
                </div>
                {process.tags && process.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {process.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-background-tertiary text-foreground-muted px-2 py-0.5 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="card">
          <div className="border-b border-border overflow-x-auto">
            <nav className="flex -mb-px">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                    activeTab === tab.key
                      ? "border-coral-500 text-coral-500"
                      : "border-transparent text-foreground-muted hover:text-foreground hover:border-border"
                  )}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div className="p-6">{renderTabContent()}</div>
        </div>
      </div>
    </div>
  );
}
