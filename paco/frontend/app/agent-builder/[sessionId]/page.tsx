"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useBuilderStore } from "@/components/agent-builder/store";
import { useBuilderStream } from "@/components/agent-builder/useBuilderStream";
import { BuilderChat } from "@/components/agent-builder/BuilderChat";
import { BuilderInput } from "@/components/agent-builder/BuilderInput";
import { ArtifactPanel } from "@/components/agent-builder/ArtifactPanel";

const PHASE_LABELS: Record<string, string> = {
  understand: "Entendiendo",
  design: "Diseñando",
  build: "Construyendo",
  test: "Probando",
  deploy: "Desplegando",
};

const PHASE_ORDER = ["understand", "design", "build", "test", "deploy"];

export default function BuilderSessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const {
    session,
    phase,
    messages,
    showArtifactPanel,
    showSidebar,
    setSession,
    setSessionId,
    setArtifacts,
    toggleArtifactPanel,
    reset,
  } = useBuilderStore();

  const { sendMessage, isStreaming } = useBuilderStream();

  // Load session on mount
  useEffect(() => {
    reset();
    setSessionId(sessionId);

    api
      .getBuilderSession(sessionId)
      .then((data) => {
        setSession(data);

        // Reconstruct messages from conversation_history
        const history = data.conversation_history || [];
        for (const msg of history) {
          if (msg.role === "user") {
            if (typeof msg.content === "string") {
              useBuilderStore.getState().addUserMessage(msg.content);
            }
          } else if (msg.role === "assistant") {
            const content = Array.isArray(msg.content)
              ? msg.content
                  .filter((b: any) => b.type === "text")
                  .map((b: any) => b.text)
                  .join("")
              : typeof msg.content === "string"
              ? msg.content
              : "";
            if (content) {
              useBuilderStore.setState((state) => ({
                messages: [
                  ...state.messages,
                  {
                    id: `restored-${state.messages.length}`,
                    role: "assistant" as const,
                    content,
                    timestamp: Date.now(),
                  },
                ],
              }));
            }
          }
        }

        // Send first message if session is new (no conversation yet)
        if (history.length === 0 && data.draft_config?.template) {
          const templateMsg = `Quiero crear un agente usando la plantilla "${data.draft_config.template}"`;
          sendMessage(templateMsg);
        } else if (history.length === 0) {
          sendMessage(data.title);
        }
      })
      .catch(() => {
        router.push("/agent-builder");
      });

    // Load artifacts
    api
      .getBuilderArtifacts(sessionId)
      .then(setArtifacts)
      .catch(() => {});
  }, [sessionId]);

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Phase Progress */}
      {showSidebar && (
        <div className="w-64 border-r border-gray-800 flex flex-col bg-[#0d0d14]">
          {/* Header */}
          <div className="p-4 border-b border-gray-800">
            <button
              onClick={() => router.push("/agent-builder")}
              className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path
                  fillRule="evenodd"
                  d="M17 10a.75.75 0 0 1-.75.75H5.612l4.158 3.96a.75.75 0 1 1-1.04 1.08l-5.5-5.25a.75.75 0 0 1 0-1.08l5.5-5.25a.75.75 0 1 1 1.04 1.08L5.612 9.25H16.25A.75.75 0 0 1 17 10Z"
                  clipRule="evenodd"
                />
              </svg>
              Builder
            </button>
            <h2 className="text-sm font-medium mt-3 truncate">
              {session?.title || "Cargando..."}
            </h2>
          </div>

          {/* Phase Progress */}
          <div className="p-4 flex-1">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">
              Progreso
            </div>
            <div className="space-y-1">
              {PHASE_ORDER.map((p, i) => {
                const currentIdx = PHASE_ORDER.indexOf(phase);
                const isActive = p === phase;
                const isDone = i < currentIdx;
                return (
                  <div
                    key={p}
                    className={`flex items-center gap-2 p-2 rounded-md text-sm ${
                      isActive
                        ? "bg-blue-500/10 text-blue-400"
                        : isDone
                        ? "text-green-400/70"
                        : "text-gray-600"
                    }`}
                  >
                    <div
                      className={`w-2 h-2 rounded-full ${
                        isActive
                          ? "bg-blue-400"
                          : isDone
                          ? "bg-green-500"
                          : "bg-gray-700"
                      }`}
                    />
                    <span>
                      {i + 1}. {PHASE_LABELS[p]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Session Info */}
          {session && (
            <div className="p-4 border-t border-gray-800 text-xs text-gray-500">
              <div>
                Tokens: {(session.total_input_tokens + session.total_output_tokens).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Center - Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-10 border-b border-gray-800 flex items-center justify-between px-4 bg-[#0d0d14]">
          <button
            onClick={() => useBuilderStore.getState().toggleSidebar()}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-4 h-4"
            >
              <path
                fillRule="evenodd"
                d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75ZM2 10a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 10Zm0 5.25a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z"
                clipRule="evenodd"
              />
            </svg>
          </button>
          <div className="text-xs text-gray-500">
            {PHASE_LABELS[phase] || phase}
          </div>
          <button
            onClick={toggleArtifactPanel}
            className={`text-gray-500 hover:text-white transition-colors ${
              showArtifactPanel ? "text-blue-400" : ""
            }`}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-4 h-4"
            >
              <path
                fillRule="evenodd"
                d="M2 4.25A2.25 2.25 0 0 1 4.25 2h11.5A2.25 2.25 0 0 1 18 4.25v8.5A2.25 2.25 0 0 1 15.75 15h-3.105a3.501 3.501 0 0 0 1.1 1.677A.75.75 0 0 1 13.26 18H6.74a.75.75 0 0 1-.484-1.323A3.501 3.501 0 0 0 7.355 15H4.25A2.25 2.25 0 0 1 2 12.75v-8.5Zm1.5 0a.75.75 0 0 1 .75-.75h11.5a.75.75 0 0 1 .75.75v7.5a.75.75 0 0 1-.75.75H4.25a.75.75 0 0 1-.75-.75v-7.5Z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* Chat area */}
        <div className="flex-1 overflow-hidden">
          <BuilderChat />
        </div>

        {/* Input area */}
        <BuilderInput onSend={sendMessage} disabled={isStreaming} />
      </div>

      {/* Right - Artifact Panel */}
      {showArtifactPanel && (
        <div className="w-[440px] border-l border-gray-800">
          <ArtifactPanel />
        </div>
      )}
    </div>
  );
}
