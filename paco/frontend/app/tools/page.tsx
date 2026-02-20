"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  Search,
  Server,
  Wrench,
  CheckCircle,
  XCircle,
  Plus,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { Header } from "@/components/ui/Header";
import {
  api,
  McpServer,
  Tool,
  CreateMcpServerRequest,
  UpdateMcpServerRequest,
  CreateToolRequest,
  UpdateToolRequest,
} from "@/lib/api";
import { cn, formatRelativeTime, getStatusColor } from "@/lib/utils";
import { useIsAdmin } from "@/lib/auth";

// ---------------------------------------------------------------------------
// MCP Server Modal
// ---------------------------------------------------------------------------

function McpServerModal({
  server,
  onClose,
  onSaved,
}: {
  server: McpServer | null; // null = create mode
  onClose: () => void;
  onSaved: (newServer: McpServer | null) => void;
}) {
  const isEdit = server !== null;
  const queryClient = useQueryClient();

  const [name, setName] = useState(server?.name ?? "");
  const [description, setDescription] = useState(server?.description ?? "");
  const [transport, setTransport] = useState(server?.transport ?? "http");
  const [url, setUrl] = useState(server?.url ?? "");
  const [command, setCommand] = useState(server?.command ?? "");
  const [args, setArgs] = useState("");
  const [envJson, setEnvJson] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  // Proxy config state
  const [proxyEnabled, setProxyEnabled] = useState(false);
  const [proxyProtocol, setProxyProtocol] = useState<"http" | "socks5">("http");
  const [proxyServerUrl, setProxyServerUrl] = useState("");
  const [proxyUsername, setProxyUsername] = useState("");
  const [proxyPassword, setProxyPassword] = useState("");
  const [bypassPatterns, setBypassPatterns] = useState("");
  const [testResult, setTestResult] = useState<{
    success: boolean;
    latency_ms?: number | null;
    error?: string | null;
    proxy_ip?: string | null;
  } | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  // Initialize proxy state from server data
  useState(() => {
    if (server?.proxy_config) {
      setProxyEnabled(server.proxy_config.enabled ?? false);
      setProxyProtocol(server.proxy_config.protocol === "socks5" ? "socks5" : "http");
      setProxyServerUrl(server.proxy_config.url ?? "");
      setProxyUsername(server.proxy_config.auth?.username ?? "");
      setProxyPassword(server.proxy_config.auth?.password ?? "");
      setBypassPatterns((server.proxy_config.bypass_patterns ?? []).join(", "));
    }
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateMcpServerRequest) => api.createMcpServer(data),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      onSaved(created);
      onClose();
    },
    onError: (err: any) => setError(err.detail || "Failed to create server"),
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateMcpServerRequest) =>
      api.updateMcpServer(server!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      onSaved(null);
      onClose();
    },
    onError: (err: any) => setError(err.detail || "Failed to update server"),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Name is required");
      return;
    }

    if ((transport === "http" || transport === "websocket") && !url.trim()) {
      setError("URL is required for this transport");
      return;
    }

    if (transport === "stdio" && !command.trim()) {
      setError("Command is required for stdio transport");
      return;
    }

    let parsedEnv: Record<string, string> | undefined;
    try {
      const parsed = JSON.parse(envJson);
      if (typeof parsed === "object" && !Array.isArray(parsed)) {
        parsedEnv =
          Object.keys(parsed).length > 0 ? parsed : undefined;
      } else {
        setError("Env must be a JSON object");
        return;
      }
    } catch {
      setError("Invalid JSON in env vars");
      return;
    }

    const parsedArgs = args
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);

    // Build proxy config
    const proxyConfig = proxyEnabled
      ? {
          enabled: true,
          protocol: proxyProtocol,
          url: proxyServerUrl.trim(),
          ...(proxyUsername.trim()
            ? { auth: { username: proxyUsername.trim(), password: proxyPassword } }
            : {}),
          bypass_patterns: bypassPatterns
            .split(",")
            .map((p) => p.trim())
            .filter(Boolean),
        }
      : null;

    if (isEdit) {
      updateMutation.mutate({
        name: name.trim(),
        description: description || undefined,
        transport,
        url: url.trim() || undefined,
        proxy_config: proxyConfig,
        command: command.trim() || undefined,
        args: parsedArgs.length > 0 ? parsedArgs : undefined,
        env: parsedEnv,
      });
    } else {
      createMutation.mutate({
        name: name.trim(),
        description: description || undefined,
        transport,
        url: url.trim() || undefined,
        proxy_config: proxyConfig,
        command: command.trim() || undefined,
        args: parsedArgs.length > 0 ? parsedArgs : undefined,
        env: parsedEnv,
      });
    }
  }

  async function handleTestProxy() {
    if (!server?.id) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const result = await api.testServerProxy(server.id);
      setTestResult(result);
    } catch (err: any) {
      setTestResult({ success: false, error: err.detail || "Test failed" });
    } finally {
      setTestLoading(false);
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-background-secondary border border-border rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">
            {isEdit ? "Edit MCP Server" : "Create MCP Server"}
          </h2>
          <button
            onClick={onClose}
            className="text-foreground-muted hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 rounded bg-error/10 text-error text-sm">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Name <span className="text-error">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. my-mcp-server"
              className="input w-full"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What does this server provide?"
              className="input w-full"
            />
          </div>

          {/* Transport */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Transport
            </label>
            <select
              value={transport}
              onChange={(e) => setTransport(e.target.value)}
              className="input w-full"
            >
              <option value="http">HTTP</option>
              <option value="stdio">Stdio</option>
              <option value="websocket">WebSocket</option>
            </select>
          </div>

          {/* URL (http / websocket) */}
          {(transport === "http" || transport === "websocket") && (
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                URL <span className="text-error">*</span>
              </label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/mcp"
                className="input w-full"
              />
            </div>
          )}

          {/* Proxy Configuration Section */}
          {transport === "http" && (
            <div className="border border-border rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">
                  Proxy Configuration
                </h3>
                <button
                  type="button"
                  onClick={() => setProxyEnabled(!proxyEnabled)}
                  className={cn(
                    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                    proxyEnabled ? "bg-coral-500" : "bg-foreground-muted/30"
                  )}
                >
                  <span
                    className={cn(
                      "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                      proxyEnabled ? "translate-x-6" : "translate-x-1"
                    )}
                  />
                </button>
              </div>

              {proxyEnabled && (
                <>
                  {/* Protocol */}
                  <div className="flex items-center gap-4">
                    <label className="text-sm text-foreground-muted">Protocol:</label>
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="radio"
                        name="proxyProtocol"
                        value="http"
                        checked={proxyProtocol === "http"}
                        onChange={() => setProxyProtocol("http")}
                        className="accent-coral-500"
                      />
                      HTTP/HTTPS
                    </label>
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="radio"
                        name="proxyProtocol"
                        value="socks5"
                        checked={proxyProtocol === "socks5"}
                        onChange={() => setProxyProtocol("socks5")}
                        className="accent-coral-500"
                      />
                      SOCKS5
                    </label>
                  </div>

                  {/* Proxy URL */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Proxy URL <span className="text-error">*</span>
                    </label>
                    <input
                      type="text"
                      value={proxyServerUrl}
                      onChange={(e) => setProxyServerUrl(e.target.value)}
                      placeholder={
                        proxyProtocol === "socks5"
                          ? "socks5://proxy:1080"
                          : "http://proxy:3128"
                      }
                      className="input w-full"
                    />
                  </div>

                  {/* Auth */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm text-foreground-muted mb-1">
                        Username
                      </label>
                      <input
                        type="text"
                        value={proxyUsername}
                        onChange={(e) => setProxyUsername(e.target.value)}
                        placeholder="Optional"
                        className="input w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-foreground-muted mb-1">
                        Password
                      </label>
                      <input
                        type="password"
                        value={proxyPassword}
                        onChange={(e) => setProxyPassword(e.target.value)}
                        placeholder="Optional"
                        className="input w-full"
                      />
                    </div>
                  </div>

                  {/* Bypass */}
                  <div>
                    <label className="block text-sm text-foreground-muted mb-1">
                      Bypass Patterns (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={bypassPatterns}
                      onChange={(e) => setBypassPatterns(e.target.value)}
                      placeholder="*.internal.local, 10.0.0.*"
                      className="input w-full"
                    />
                  </div>

                  {/* Test Connection */}
                  {isEdit && (
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={handleTestProxy}
                        disabled={testLoading || !proxyServerUrl.trim()}
                        className="btn-ghost px-3 py-1.5 text-sm flex items-center gap-1.5"
                      >
                        {testLoading ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Search className="w-3.5 h-3.5" />
                        )}
                        Test Connection
                      </button>
                      {testResult && (
                        <span
                          className={cn(
                            "text-sm",
                            testResult.success ? "text-success" : "text-error"
                          )}
                        >
                          {testResult.success
                            ? `Connected (${testResult.latency_ms}ms) - IP: ${testResult.proxy_ip}`
                            : testResult.error}
                        </span>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Command (stdio) */}
          {transport === "stdio" && (
            <>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Command <span className="text-error">*</span>
                </label>
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="e.g. npx"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Args (comma-separated)
                </label>
                <input
                  type="text"
                  value={args}
                  onChange={(e) => setArgs(e.target.value)}
                  placeholder="e.g. -y, @modelcontextprotocol/server-filesystem"
                  className="input w-full"
                />
              </div>
            </>
          )}

          {/* Env vars */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Env Variables (JSON)
            </label>
            <textarea
              value={envJson}
              onChange={(e) => setEnvJson(e.target.value)}
              rows={3}
              placeholder='{"API_KEY": "..."}'
              className="input w-full font-mono text-sm"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost px-4 py-2"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="btn-primary px-4 py-2"
            >
              {isPending ? "Saving..." : isEdit ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tool Modal
// ---------------------------------------------------------------------------

function ToolModal({
  tool,
  servers,
  onClose,
  onSaved,
}: {
  tool: Tool | null; // null = create mode
  servers: McpServer[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = tool !== null;
  const queryClient = useQueryClient();

  const [name, setName] = useState(tool?.name ?? "");
  const [description, setDescription] = useState(tool?.description ?? "");
  const [mcpServerId, setMcpServerId] = useState(tool?.mcp_server_id ?? "");
  const [inputSchemaJson, setInputSchemaJson] = useState(
    tool?.input_schema ? JSON.stringify(tool.input_schema, null, 2) : "{}"
  );
  const [isEnabled, setIsEnabled] = useState(tool?.is_enabled ?? true);
  const [error, setError] = useState<string | null>(null);

  // State for inline MCP server creation
  const [showServerModal, setShowServerModal] = useState(false);

  const createMutation = useMutation({
    mutationFn: (data: CreateToolRequest) => api.createTool(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      onSaved();
      onClose();
    },
    onError: (err: any) => setError(err.detail || "Failed to create tool"),
  });

  const updateMutation = useMutation({
    mutationFn: (data: UpdateToolRequest) => api.updateTool(tool!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      onSaved();
      onClose();
    },
    onError: (err: any) => setError(err.detail || "Failed to update tool"),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    let parsedInputSchema: Record<string, any>;
    try {
      parsedInputSchema = JSON.parse(inputSchemaJson);
      if (
        typeof parsedInputSchema !== "object" ||
        Array.isArray(parsedInputSchema)
      ) {
        setError("Input schema must be a JSON object");
        return;
      }
    } catch {
      setError("Invalid JSON in input schema");
      return;
    }

    if (isEdit) {
      updateMutation.mutate({
        description: description || undefined,
        input_schema: parsedInputSchema,
        is_enabled: isEnabled,
      });
    } else {
      if (!name.trim()) {
        setError("Name is required");
        return;
      }
      createMutation.mutate({
        name: name.trim(),
        description: description || undefined,
        mcp_server_id: mcpServerId || undefined,
        input_schema: parsedInputSchema,
      });
    }
  }

  function handleServerSelect(value: string) {
    if (value === "__new__") {
      setShowServerModal(true);
    } else {
      setMcpServerId(value);
    }
  }

  function handleServerCreated(newServer: McpServer | null) {
    if (newServer) {
      setMcpServerId(newServer.id);
    }
    setShowServerModal(false);
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={onClose} />
        <div className="relative bg-background-secondary border border-border rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
          <div className="flex items-center justify-between p-4 border-b border-border">
            <h2 className="text-lg font-semibold text-foreground">
              {isEdit ? "Edit Tool" : "Create Tool"}
            </h2>
            <button
              onClick={onClose}
              className="text-foreground-muted hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            {error && (
              <div className="p-3 rounded bg-error/10 text-error text-sm">
                {error}
              </div>
            )}

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Name <span className="text-error">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isEdit}
                placeholder="e.g. search_documents"
                className={cn(
                  "input w-full",
                  isEdit && "opacity-50 cursor-not-allowed"
                )}
              />
              {isEdit && (
                <p className="text-xs text-foreground-muted mt-1">
                  Name cannot be changed
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="What does this tool do?"
                className="input w-full"
              />
            </div>

            {/* MCP Server */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                MCP Server
              </label>
              <select
                value={mcpServerId}
                onChange={(e) => handleServerSelect(e.target.value)}
                disabled={isEdit}
                className={cn(
                  "input w-full",
                  isEdit && "opacity-50 cursor-not-allowed"
                )}
              >
                <option value="">None</option>
                {servers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
                {!isEdit && (
                  <option value="__new__">+ Create new server...</option>
                )}
              </select>
            </div>

            {/* Input Schema */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Input Schema (JSON)
              </label>
              <textarea
                value={inputSchemaJson}
                onChange={(e) => setInputSchemaJson(e.target.value)}
                rows={6}
                className="input w-full font-mono text-sm"
              />
            </div>

            {/* Is Enabled (edit only) */}
            {isEdit && (
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-foreground">
                  Enabled
                </label>
                <button
                  type="button"
                  onClick={() => setIsEnabled(!isEnabled)}
                  className={cn(
                    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                    isEnabled ? "bg-coral-500" : "bg-foreground-muted/30"
                  )}
                >
                  <span
                    className={cn(
                      "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                      isEnabled ? "translate-x-6" : "translate-x-1"
                    )}
                  />
                </button>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-2 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                className="btn-ghost px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="btn-primary px-4 py-2"
              >
                {isPending ? "Saving..." : isEdit ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Inline server creation modal (stacks above) */}
      {showServerModal && (
        <McpServerModal
          server={null}
          onClose={() => setShowServerModal(false)}
          onSaved={handleServerCreated}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Delete Tool Confirmation
// ---------------------------------------------------------------------------

function DeleteToolConfirmation({
  tool,
  onClose,
  onConfirm,
  isPending,
}: {
  tool: Tool;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-background-secondary border border-border rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-lg font-semibold text-foreground mb-2">
          Delete Tool
        </h2>
        <p className="text-sm text-foreground-muted mb-4">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{tool.name}</span>?
          This action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <button onClick={onClose} className="btn-ghost px-4 py-2">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 rounded-md bg-error text-white hover:bg-error/90 transition-colors disabled:opacity-50"
          >
            {isPending ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delete Server Confirmation
// ---------------------------------------------------------------------------

function DeleteServerConfirmation({
  server,
  onClose,
  onConfirm,
  isPending,
}: {
  server: McpServer;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-background-secondary border border-border rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-lg font-semibold text-foreground mb-2">
          Delete MCP Server
        </h2>
        <p className="text-sm text-foreground-muted mb-4">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{server.name}</span>?
          This will also delete all tools associated with this server. This
          action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <button onClick={onClose} className="btn-ghost px-4 py-2">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 rounded-md bg-error text-white hover:bg-error/90 transition-colors disabled:opacity-50"
          >
            {isPending ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ToolsPage() {
  const queryClient = useQueryClient();
  const isAdmin = useIsAdmin();
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Modal state: undefined = closed, null = create, object = edit
  const [toolModalTarget, setToolModalTarget] = useState<
    Tool | null | undefined
  >(undefined);
  const [serverModalTarget, setServerModalTarget] = useState<
    McpServer | null | undefined
  >(undefined);
  const [deleteToolTarget, setDeleteToolTarget] = useState<Tool | null>(null);
  const [deleteServerTarget, setDeleteServerTarget] =
    useState<McpServer | null>(null);

  // Fetch MCP servers
  const { data: servers = [], isLoading: serversLoading } = useQuery({
    queryKey: ["mcp-servers"],
    queryFn: () => api.getMcpServers(),
  });

  // Fetch tools
  const { data: tools = [], isLoading: toolsLoading } = useQuery({
    queryKey: ["tools", selectedServer],
    queryFn: () => api.getTools(selectedServer || undefined),
  });

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: (serverId: string) => api.checkMcpServerHealth(serverId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] }),
  });

  // Sync tools mutation
  const syncToolsMutation = useMutation({
    mutationFn: (serverId: string) => api.syncToolsFromServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
    },
  });

  // Delete tool mutation
  const deleteToolMutation = useMutation({
    mutationFn: (id: string) => api.deleteTool(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      setDeleteToolTarget(null);
    },
  });

  // Delete server mutation
  const deleteServerMutation = useMutation({
    mutationFn: (id: string) => api.deleteMcpServer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      setDeleteServerTarget(null);
      if (deleteServerTarget && selectedServer === deleteServerTarget.id) {
        setSelectedServer(null);
      }
    },
  });

  // Filter tools
  const filteredTools = tools.filter(
    (tool) =>
      tool.name.toLowerCase().includes(search.toLowerCase()) ||
      tool.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <Header title="Tools" description="MCP servers and tool registry" />

      <div className="p-6">
        <div className="grid grid-cols-4 gap-6">
          {/* MCP Servers Sidebar */}
          <div className="col-span-1">
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="font-semibold text-foreground">MCP Servers</h2>
                {isAdmin && (
                  <button
                    onClick={() => setServerModalTarget(null)}
                    className="text-foreground-muted hover:text-coral-500 transition-colors"
                    title="Add MCP Server"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                )}
              </div>
              <div className="p-2">
                {serversLoading ? (
                  <div className="h-32 flex items-center justify-center">
                    <div className="animate-spin w-6 h-6 border-2 border-coral-500 border-t-transparent rounded-full" />
                  </div>
                ) : servers.length === 0 ? (
                  <p className="text-center text-foreground-muted py-4 text-sm">
                    No MCP servers configured
                  </p>
                ) : (
                  <div className="space-y-1">
                    {/* All tools option */}
                    <button
                      onClick={() => setSelectedServer(null)}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors",
                        selectedServer === null
                          ? "bg-coral-500/10 text-coral-500"
                          : "hover:bg-background-tertiary text-foreground-muted hover:text-foreground"
                      )}
                    >
                      <Wrench className="w-4 h-4" />
                      <span className="flex-1">All Tools</span>
                      <span className="text-xs">{tools.length}</span>
                    </button>

                    {/* Server list */}
                    {servers.map((server) => (
                      <div key={server.id} className="group">
                        <button
                          onClick={() => setSelectedServer(server.id)}
                          className={cn(
                            "w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors",
                            selectedServer === server.id
                              ? "bg-coral-500/10 text-coral-500"
                              : "hover:bg-background-tertiary text-foreground-muted hover:text-foreground"
                          )}
                        >
                          <Server className="w-4 h-4" />
                          <span className="flex-1 truncate">{server.name}</span>
                          <span
                            className={cn(
                              "w-2 h-2 rounded-full",
                              server.status === "online"
                                ? "bg-success"
                                : server.status === "offline"
                                ? "bg-error"
                                : "bg-foreground-muted"
                            )}
                          />
                        </button>

                        {/* Server actions */}
                        <div className="flex items-center gap-1 px-3 pb-2">
                          <button
                            onClick={() =>
                              healthCheckMutation.mutate(server.id)
                            }
                            disabled={healthCheckMutation.isPending}
                            className="text-xs text-foreground-muted hover:text-foreground"
                            title="Check health"
                          >
                            <RefreshCw
                              className={cn(
                                "w-3 h-3",
                                healthCheckMutation.isPending && "animate-spin"
                              )}
                            />
                          </button>
                          {isAdmin && server.transport === "http" && (
                            <button
                              onClick={() =>
                                syncToolsMutation.mutate(server.id)
                              }
                              disabled={syncToolsMutation.isPending}
                              className="text-xs text-coral-500 hover:text-coral-400 ml-2"
                            >
                              Sync
                            </button>
                          )}
                          {isAdmin && (
                            <>
                              <button
                                onClick={() => setServerModalTarget(server)}
                                className="text-xs text-foreground-muted hover:text-foreground ml-2"
                                title="Edit server"
                              >
                                <Pencil className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => setDeleteServerTarget(server)}
                                className="text-xs text-foreground-muted hover:text-error ml-1"
                                title="Delete server"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tools List */}
          <div className="col-span-3">
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="font-semibold text-foreground">
                  Tools{" "}
                  {selectedServer &&
                    servers.find((s) => s.id === selectedServer) && (
                      <span className="text-foreground-muted font-normal">
                        from{" "}
                        {
                          servers.find((s) => s.id === selectedServer)
                            ?.name
                        }
                      </span>
                    )}
                </h2>
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                    <input
                      type="text"
                      placeholder="Search tools..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="input pl-9 w-64"
                    />
                  </div>
                  {isAdmin && (
                    <button
                      onClick={() => setToolModalTarget(null)}
                      className="btn-primary px-3 py-1.5 text-sm flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      New Tool
                    </button>
                  )}
                </div>
              </div>

              <div className="p-4">
                {toolsLoading ? (
                  <div className="h-64 flex items-center justify-center">
                    <div className="animate-spin w-8 h-8 border-2 border-coral-500 border-t-transparent rounded-full" />
                  </div>
                ) : filteredTools.length === 0 ? (
                  <div className="h-64 flex items-center justify-center text-foreground-muted">
                    {search
                      ? "No tools match your search"
                      : "No tools registered"}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredTools.map((tool) => (
                      <div
                        key={tool.id}
                        onClick={() => isAdmin && setToolModalTarget(tool)}
                        className={cn(
                          "flex items-start gap-4 p-4 rounded-lg bg-background-tertiary hover:bg-border/50 transition-colors",
                          isAdmin && "cursor-pointer"
                        )}
                      >
                        <div
                          className={cn(
                            "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
                            tool.is_enabled
                              ? "bg-success/20"
                              : "bg-foreground-muted/20"
                          )}
                        >
                          <Wrench
                            className={cn(
                              "w-5 h-5",
                              tool.is_enabled
                                ? "text-success"
                                : "text-foreground-muted"
                            )}
                          />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-foreground">
                              {tool.name}
                            </h3>
                            {tool.mcp_server_name && (
                              <span className="text-xs text-foreground-muted bg-background-secondary px-2 py-0.5 rounded">
                                {tool.mcp_server_name}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-foreground-muted mt-1">
                            {tool.description || "No description"}
                          </p>

                          {/* Input Schema Preview */}
                          {Object.keys(tool.input_schema).length > 0 && (
                            <details className="mt-2">
                              <summary className="text-xs text-coral-500 cursor-pointer hover:text-coral-400">
                                View schema
                              </summary>
                              <pre className="mt-2 p-2 rounded bg-background text-xs text-foreground-muted overflow-x-auto">
                                {JSON.stringify(tool.input_schema, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>

                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          {isAdmin && (
                            <>
                              <button
                                onClick={() => setToolModalTarget(tool)}
                                className="text-foreground-muted hover:text-foreground transition-colors"
                                title="Edit tool"
                              >
                                <Pencil className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setDeleteToolTarget(tool)}
                                className="text-foreground-muted hover:text-error transition-colors"
                                title="Delete tool"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          {tool.is_enabled ? (
                            <CheckCircle className="w-5 h-5 text-success" />
                          ) : (
                            <XCircle className="w-5 h-5 text-foreground-muted" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {toolModalTarget !== undefined && (
        <ToolModal
          tool={toolModalTarget}
          servers={servers}
          onClose={() => setToolModalTarget(undefined)}
          onSaved={() => {}}
        />
      )}

      {serverModalTarget !== undefined && (
        <McpServerModal
          server={serverModalTarget}
          onClose={() => setServerModalTarget(undefined)}
          onSaved={() => {}}
        />
      )}

      {deleteToolTarget && (
        <DeleteToolConfirmation
          tool={deleteToolTarget}
          onClose={() => setDeleteToolTarget(null)}
          onConfirm={() => deleteToolMutation.mutate(deleteToolTarget.id)}
          isPending={deleteToolMutation.isPending}
        />
      )}

      {deleteServerTarget && (
        <DeleteServerConfirmation
          server={deleteServerTarget}
          onClose={() => setDeleteServerTarget(null)}
          onConfirm={() =>
            deleteServerMutation.mutate(deleteServerTarget.id)
          }
          isPending={deleteServerMutation.isPending}
        />
      )}
    </div>
  );
}
