"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, BuilderSession } from "@/lib/api";

const TEMPLATES = [
  {
    id: "vehicles",
    name: "Trámites Vehiculares",
    description: "Placas, tenencia, verificación, infracciones",
    icon: "🚗",
  },
  {
    id: "water",
    name: "Servicios de Agua",
    description: "Consulta de consumo, reportes, reconexión",
    icon: "💧",
  },
  {
    id: "property-tax",
    name: "Pago de Predial",
    description: "Consulta y pago de impuesto predial",
    icon: "🏠",
  },
  {
    id: "citizen-attention",
    name: "Atención Ciudadana",
    description: "Quejas, sugerencias, seguimiento",
    icon: "👤",
  },
  {
    id: "education",
    name: "Servicios Educativos",
    description: "Preinscripciones, certificados, becas",
    icon: "📚",
  },
  {
    id: "custom",
    name: "Personalizado",
    description: "Empieza desde cero con tu propio servicio",
    icon: "✨",
  },
];

export default function AgentBuilderLanding() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [recentSessions, setRecentSessions] = useState<BuilderSession[]>([]);

  useEffect(() => {
    api.getBuilderSessions().then(setRecentSessions).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim() || isCreating) return;
    await createSession(prompt.trim());
  }

  async function handleTemplate(templateId: string) {
    const template = TEMPLATES.find((t) => t.id === templateId);
    const templatePrompt =
      templateId === "custom"
        ? "Quiero crear un agente de gobierno"
        : `Quiero crear un agente para ${template?.name?.toLowerCase()}`;
    await createSession(templatePrompt, templateId);
  }

  async function createSession(text: string, templateId?: string) {
    setIsCreating(true);
    try {
      const session = await api.createBuilderSession({
        prompt: text,
        template_id: templateId,
      });
      router.push(`/agent-builder/${session.id}`);
    } catch (err: any) {
      console.error("Failed to create session:", err);
      setIsCreating(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold mb-3">
          Agent Builder
        </h1>
        <p className="text-gray-400 text-lg max-w-xl">
          Describe el servicio de gobierno que quieres automatizar y te ayudaré
          a construir un agente completo con herramientas, skills y prompts.
        </p>
      </div>

      {/* Hero Input */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl mb-12">
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe el servicio que quieres automatizar... (ej: 'Quiero que los ciudadanos puedan consultar y pagar su predial')"
            className="w-full h-32 p-4 pr-16 bg-[#1a1a24] border border-gray-700 rounded-xl text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-base"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!prompt.trim() || isCreating}
            className="absolute right-3 bottom-3 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {isCreating ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
              </svg>
            )}
          </button>
        </div>
      </form>

      {/* Template Cards */}
      <div className="w-full max-w-4xl mb-12">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
          Plantillas de inicio rápido
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {TEMPLATES.map((template) => (
            <button
              key={template.id}
              onClick={() => handleTemplate(template.id)}
              disabled={isCreating}
              className="p-4 bg-[#1a1a24] border border-gray-700/50 rounded-xl text-left hover:border-blue-500/50 hover:bg-[#1e1e2e] transition-all disabled:opacity-50"
            >
              <div className="text-2xl mb-2">{template.icon}</div>
              <div className="font-medium text-sm mb-1">{template.name}</div>
              <div className="text-xs text-gray-500">
                {template.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Sessions */}
      {recentSessions.length > 0 && (
        <div className="w-full max-w-4xl">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
            Sesiones recientes
          </h2>
          <div className="space-y-2">
            {recentSessions.slice(0, 5).map((session) => (
              <button
                key={session.id}
                onClick={() => router.push(`/agent-builder/${session.id}`)}
                className="w-full p-3 bg-[#1a1a24] border border-gray-700/50 rounded-lg text-left hover:border-gray-600 transition-colors flex items-center justify-between"
              >
                <div>
                  <div className="font-medium text-sm">{session.title}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {session.phase} &middot;{" "}
                    {new Date(session.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      session.status === "active"
                        ? "bg-green-500"
                        : session.status === "completed"
                        ? "bg-blue-500"
                        : "bg-gray-500"
                    }`}
                  />
                  <span className="text-xs text-gray-500">
                    {session.status}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Back link */}
      <button
        onClick={() => router.push("/dashboard")}
        className="mt-8 text-sm text-gray-500 hover:text-gray-300 transition-colors"
      >
        ← Volver al Dashboard
      </button>
    </div>
  );
}
