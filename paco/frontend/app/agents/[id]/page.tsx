"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useParams } from "next/navigation";
import {
  ArrowLeft,
  Play,
  Square,
  RotateCw,
  Pencil,
  Trash2,
  Save,
  X,
} from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/ui/Header";
import { api, AgentDetail, ApiError } from "@/lib/api";
import { cn, getStatusColor, formatRelativeTime } from "@/lib/utils";
import { useIsOperator } from "@/lib/auth";

export default function AgentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();
  const isOperator = useIsOperator();

  const [editing, setEditing] = useState(false);
  const [editYaml, setEditYaml] = useState("");
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    data: agent,
    isLoading,
    error: fetchError,
  } = useQuery({
    queryKey: ["agent", id],
    queryFn: () => api.getAgent(id),
    refetchInterval: 15000,
  });

  const startEditing = () => {
    if (!agent) return;
    setEditDisplayName(agent.display_name || "");
    setEditDescription(agent.description || "");
    setEditYaml(
      agent.config ? yamlFromConfig(agent.config) : ""
    );
    setEditing(true);
    setError(null);
  };

  const cancelEditing = () => {
    setEditing(false);
    setError(null);
  };

  // Mutations
  const startMutation = useMutation({
    mutationFn: () => api.startAgent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agent", id] }),
  });

  const stopMutation = useMutation({
    mutationFn: () => api.stopAgent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agent", id] }),
  });

  const restartMutation = useMutation({
    mutationFn: () => api.restartAgent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agent", id] }),
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updateAgent(id, {
        display_name: editDisplayName || undefined,
        description: editDescription || undefined,
        config_yaml: editYaml || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent", id] });
      setEditing(false);
      setError(null);
    },
    onError: (err: ApiError) => {
      setError(err.detail || "Failed to update agent");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteAgent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      router.push("/agents");
    },
    onError: (err: ApiError) => {
      setError(err.detail || "Failed to delete agent");
    },
  });

  if (isLoading) {
    return (
      <div>
        <Header title="Agent" />
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-coral-500 border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (fetchError || !agent) {
    return (
      <div>
        <Header title="Agent" />
        <div className="p-6">
          <Link
            href="/agents"
            className="inline-flex items-center gap-1 text-sm text-foreground-muted hover:text-foreground mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Agents
          </Link>
          <div className="card p-8 text-center">
            <p className="text-foreground-muted">
              Agent not found or failed to load.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isRunning = agent.status === "running";
  const isStopped = agent.status === "stopped";
  const lifecycleLoading =
    startMutation.isPending ||
    stopMutation.isPending ||
    restartMutation.isPending;

  return (
    <div>
      <Header
        title={agent.display_name || agent.name}
        description={agent.description || undefined}
      />

      <div className="p-6 space-y-6 max-w-4xl">
        <Link
          href="/agents"
          className="inline-flex items-center gap-1 text-sm text-foreground-muted hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Agents
        </Link>

        {error && (
          <div className="p-3 rounded-lg bg-error/10 border border-error/30 text-error text-sm">
            {error}
          </div>
        )}

        {/* Agent Info Card */}
        <div className="card p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                {agent.display_name || agent.name}
              </h2>
              <p className="text-sm text-foreground-muted">{agent.name}</p>
            </div>
            <span
              className={cn(
                "px-3 py-1 rounded-full text-sm font-medium",
                getStatusColor(agent.status)
              )}
            >
              {agent.status}
            </span>
          </div>

          {agent.description && !editing && (
            <p className="text-sm text-foreground-muted mb-4">
              {agent.description}
            </p>
          )}

          {/* Meta info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-foreground-muted">Type</p>
              <p className="font-medium text-foreground">{agent.type}</p>
            </div>
            <div>
              <p className="text-foreground-muted">Version</p>
              <p className="font-medium text-foreground">v{agent.version}</p>
            </div>
            {agent.port && (
              <div>
                <p className="text-foreground-muted">Port</p>
                <p className="font-medium text-foreground">{agent.port}</p>
              </div>
            )}
            {agent.last_health_check && (
              <div>
                <p className="text-foreground-muted">Last Health Check</p>
                <p className="font-medium text-foreground">
                  {formatRelativeTime(agent.last_health_check)}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
            <Link href={`/agents/${id}/playground`} className="btn-primary btn-sm">
              <Play className="w-3.5 h-3.5 mr-1" />
              Playground
            </Link>
          </div>

          {/* Lifecycle controls */}
          {isOperator && (
            <div className="flex items-center gap-2 mt-2">
              {isStopped && (
                <button
                  onClick={() => startMutation.mutate()}
                  disabled={lifecycleLoading}
                  className="btn-primary btn-sm"
                >
                  <Play className="w-3.5 h-3.5 mr-1" />
                  Start
                </button>
              )}
              {isRunning && (
                <>
                  <button
                    onClick={() => stopMutation.mutate()}
                    disabled={lifecycleLoading}
                    className="btn-secondary btn-sm"
                  >
                    <Square className="w-3.5 h-3.5 mr-1" />
                    Stop
                  </button>
                  <button
                    onClick={() => restartMutation.mutate()}
                    disabled={lifecycleLoading}
                    className="btn-secondary btn-sm"
                  >
                    <RotateCw className="w-3.5 h-3.5 mr-1" />
                    Restart
                  </button>
                </>
              )}
              {lifecycleLoading && (
                <div className="animate-spin w-4 h-4 border-2 border-coral-500 border-t-transparent rounded-full ml-2" />
              )}
            </div>
          )}
        </div>

        {/* Configuration Card */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-md font-semibold text-foreground">
              Configuration
            </h3>
            {isOperator && !editing && (
              <button onClick={startEditing} className="btn-secondary btn-sm">
                <Pencil className="w-3.5 h-3.5 mr-1" />
                Edit
              </button>
            )}
          </div>

          {editing ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={editDisplayName}
                  onChange={(e) => setEditDisplayName(e.target.value)}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Description
                </label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={2}
                  className="input w-full resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  YAML Config
                </label>
                <textarea
                  value={editYaml}
                  onChange={(e) => setEditYaml(e.target.value)}
                  rows={16}
                  className="input w-full font-mono text-sm resize-y"
                  spellCheck={false}
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => updateMutation.mutate()}
                  disabled={updateMutation.isPending}
                  className="btn-primary btn-sm"
                >
                  <Save className="w-3.5 h-3.5 mr-1" />
                  {updateMutation.isPending ? "Saving..." : "Save"}
                </button>
                <button onClick={cancelEditing} className="btn-secondary btn-sm">
                  <X className="w-3.5 h-3.5 mr-1" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <pre className="bg-background-tertiary p-4 rounded-lg text-sm text-foreground font-mono overflow-x-auto whitespace-pre-wrap">
              {agent.config && Object.keys(agent.config).length > 0
                ? yamlFromConfig(agent.config)
                : "No configuration available"}
            </pre>
          )}
        </div>

        {/* Danger Zone */}
        {isOperator && (
          <div className="card p-6 border-error/30">
            <h3 className="text-md font-semibold text-error mb-2">
              Danger Zone
            </h3>
            <p className="text-sm text-foreground-muted mb-4">
              Permanently delete this agent. This action cannot be undone.
            </p>

            {showDeleteConfirm ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                  className="btn-md bg-error text-white hover:bg-error/80"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  {deleteMutation.isPending
                    ? "Deleting..."
                    : "Yes, Delete Agent"}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="btn-secondary btn-md"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="btn-md bg-error/10 text-error hover:bg-error/20 border border-error/30"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete Agent
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Simple pretty-print of a config object as YAML-like text */
function yamlFromConfig(config: Record<string, any>, indent = 0): string {
  const pad = "  ".repeat(indent);
  const lines: string[] = [];

  for (const [key, value] of Object.entries(config)) {
    if (value === null || value === undefined) {
      lines.push(`${pad}${key}:`);
    } else if (typeof value === "object" && !Array.isArray(value)) {
      lines.push(`${pad}${key}:`);
      lines.push(yamlFromConfig(value, indent + 1));
    } else if (Array.isArray(value)) {
      lines.push(`${pad}${key}:`);
      for (const item of value) {
        if (typeof item === "object") {
          lines.push(`${pad}  -`);
          lines.push(yamlFromConfig(item, indent + 2));
        } else {
          lines.push(`${pad}  - ${item}`);
        }
      }
    } else {
      lines.push(`${pad}${key}: ${value}`);
    }
  }

  return lines.join("\n");
}
