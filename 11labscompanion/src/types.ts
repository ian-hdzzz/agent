/**
 * 11LabsCompanion Type Definitions
 * Claude Agent SDK powered ElevenLabs companion
 */

// ============================================================
// Skill Category Codes
// ============================================================

export type SkillCode =
  | "VOI"   // Voice Management
  | "AGT"   // Agent Management
  | "TLS"   // Tools Management
  | "KNB"   // Knowledge Base
  | "AUD"   // Audio Generation (TTS/STT/SFX)
  | "CNV"   // Conversations
  | "ACC";  // Account & Subscription

// ============================================================
// Workflow Types
// ============================================================

export interface WorkflowInput {
  input_as_text: string;
  conversationId?: string;
  metadata?: {
    name?: string;
    userId?: string;
  };
}

export interface WorkflowOutput {
  output_text: string;
  skill?: SkillCode;
  toolsUsed?: string[];
  error?: string;
}

// ============================================================
// Voice Types
// ============================================================

export interface Voice {
  voice_id: string;
  name: string;
  category?: string;
  description?: string;
  labels?: Record<string, string>;
  preview_url?: string;
  settings?: VoiceSettings;
}

export interface VoiceSettings {
  stability: number;
  similarity_boost: number;
  style?: number;
  use_speaker_boost?: boolean;
  speed?: number;
}

// ============================================================
// Agent Types
// ============================================================

export interface Agent {
  agent_id: string;
  name: string;
  created_at?: string;
  conversation_config?: ConversationConfig;
  platform_settings?: PlatformSettings;
  tags?: string[];
}

export interface ConversationConfig {
  agent?: {
    prompt?: {
      prompt?: string;
      llm?: string;
      temperature?: number;
      tools?: AgentTool[];
      knowledge_base?: string[];
    };
    first_message?: string;
    language?: string;
  };
  tts?: {
    model_id?: string;
    voice_id?: string;
    stability?: number;
    similarity_boost?: number;
  };
  asr?: {
    quality?: 'high' | 'low';
  };
  conversation?: {
    max_duration_seconds?: number;
  };
}

export interface PlatformSettings {
  auth?: { enable_auth?: boolean };
  widget?: { variant?: string };
  data_collection?: { record_voice?: boolean; retention_days?: number };
}

export interface AgentTool {
  type: 'webhook' | 'client';
  name: string;
  description: string;
  parameters?: ToolParameter[];
  api_schema?: { url: string; method: string; headers?: Record<string, string> };
}

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required?: boolean;
}

// ============================================================
// Tool Types
// ============================================================

export interface Tool {
  tool_id: string;
  type: 'webhook' | 'client';
  name: string;
  description: string;
  parameters?: ToolParameter[];
  api_schema?: { url: string; method: string };
}

// ============================================================
// Knowledge Base Types
// ============================================================

export interface KnowledgeBaseDocument {
  document_id: string;
  name: string;
  type?: string;
  description?: string;
  status?: 'pending' | 'processing' | 'ready' | 'failed';
  created_at?: string;
}

// ============================================================
// Conversation Types
// ============================================================

export interface Conversation {
  conversation_id: string;
  agent_id?: string;
  status?: string;
  start_time?: string;
  duration_seconds?: number;
  transcript?: TranscriptEntry[];
}

export interface TranscriptEntry {
  role: 'user' | 'agent';
  message: string;
  timestamp?: string;
  tool_calls?: { tool_name: string; parameters: Record<string, unknown> }[];
}

// ============================================================
// Subscription Types
// ============================================================

export interface Subscription {
  tier: string;
  character_count: number;
  character_limit: number;
  voice_limit: number;
  professional_voice_limit: number;
  can_use_instant_voice_cloning: boolean;
  can_use_professional_voice_cloning: boolean;
  next_character_count_reset_unix: number;
  status: string;
}

// ============================================================
// Model Types
// ============================================================

export interface Model {
  model_id: string;
  name: string;
  can_do_text_to_speech: boolean;
  can_do_voice_conversion: boolean;
  languages: { language_id: string; name: string }[];
  description: string;
}

// ============================================================
// Phone Number Types
// ============================================================

export interface PhoneNumber {
  phone_number_id: string;
  phone_number: string;
  label?: string;
  assigned_agent_id?: string;
  provider?: string;
}
