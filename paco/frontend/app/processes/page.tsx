"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  FileText,
  CheckCircle,
  Loader2,
  AlertTriangle,
  BarChart3,
} from "lucide-react";
import { Header } from "@/components/ui/Header";
import { ProcessCard } from "@/components/processes/ProcessCard";
import { api, Process } from "@/lib/api";
import { cn } from "@/lib/utils";

type StatusFilter = "all" | "analyzing" | "completed" | "error";

export default function ProcessesPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");

  const { data: processes = [], isLoading } = useQuery({
    queryKey: ["processes"],
    queryFn: () => api.getProcesses(),
  });

  // Compute counts
  const counts = useMemo(() => {
    const total = processes.length;
    const completed = processes.filter((p) => p.status === "completed").length;
    const analyzing = processes.filter((p) => p.status === "analyzing").length;
    const error = processes.filter((p) => p.status === "error").length;
    return { total, completed, analyzing, error };
  }, [processes]);

  // Filter processes
  const filteredProcesses = useMemo(() => {
    return processes.filter((process) => {
      if (statusFilter !== "all" && process.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          process.name.toLowerCase().includes(q) ||
          process.department.toLowerCase().includes(q) ||
          process.description?.toLowerCase().includes(q) ||
          process.tags?.some((t) => t.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [processes, statusFilter, search]);

  const stats = [
    {
      label: "Total",
      value: counts.total,
      icon: FileText,
      color: "text-foreground",
      bg: "bg-foreground/10",
    },
    {
      label: "Completados",
      value: counts.completed,
      icon: CheckCircle,
      color: "text-success",
      bg: "bg-success/10",
    },
    {
      label: "Analizando",
      value: counts.analyzing,
      icon: Loader2,
      color: "text-amber-400",
      bg: "bg-amber-400/10",
    },
    {
      label: "Error",
      value: counts.error,
      icon: AlertTriangle,
      color: "text-error",
      bg: "bg-error/10",
    },
  ];

  return (
    <div>
      <Header
        title="Procesos Mapeados"
        description="Procesos gubernamentales analizados y optimizados"
      />

      <div className="p-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="card p-4 flex items-center gap-4"
            >
              <div
                className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center",
                  stat.bg
                )}
              >
                <stat.icon className={cn("w-5 h-5", stat.color)} />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {stat.value}
                </p>
                <p className="text-xs text-foreground-muted">{stat.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filter bar */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="font-semibold text-foreground">
                Procesos{" "}
                <span className="text-foreground-muted font-normal text-sm">
                  ({filteredProcesses.length})
                </span>
              </h2>

              {/* Status toggle */}
              <div className="flex items-center gap-1 bg-background-tertiary rounded-lg p-0.5">
                {(
                  [
                    ["all", `Todos (${counts.total})`],
                    ["analyzing", `Analizando (${counts.analyzing})`],
                    ["completed", `Completado (${counts.completed})`],
                    ["error", `Error (${counts.error})`],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    onClick={() => setStatusFilter(value)}
                    className={cn(
                      "px-3 py-1 rounded-md text-xs transition-colors",
                      statusFilter === value
                        ? "bg-background text-foreground shadow-sm"
                        : "text-foreground-muted hover:text-foreground"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Buscar procesos..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-9 w-64"
                />
              </div>
            </div>
          </div>

          {/* Process grid */}
          <div className="p-4">
            {isLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="animate-spin w-8 h-8 border-2 border-coral-500 border-t-transparent rounded-full" />
              </div>
            ) : filteredProcesses.length === 0 ? (
              <div className="h-64 flex flex-col items-center justify-center text-foreground-muted">
                <BarChart3 className="w-12 h-12 mb-3 opacity-30" />
                <p>
                  {search || statusFilter !== "all"
                    ? "No se encontraron procesos con esos filtros"
                    : "No hay procesos registrados"}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredProcesses.map((process) => (
                  <ProcessCard key={process.id} process={process} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
