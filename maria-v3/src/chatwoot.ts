// ============================================
// Maria V3 - Chatwoot/Agora Integration Module
// ============================================

import type { ChatwootWebhookPayload, ChatwootAttachment } from "./types.js";
import { processMediaAttachments } from "./media.js";
import { logger } from "./utils/logger.js";
import { config } from "./config/index.js";

// ============================================
// Configuration
// ============================================

const CHATWOOT_BASE_URL = config.chatwoot.baseUrl;
const CHATWOOT_API_TOKEN = config.chatwoot.apiToken;

// Track processed message IDs to avoid duplicates
const processedMessages = new Set<number>();
const MESSAGE_CACHE_TTL = 60000; // 1 minute

// ============================================
// Send Message to Chatwoot
// ============================================

export async function sendToChatwoot(
    accountId: number,
    conversationId: number,
    message: string
): Promise<{ success: boolean; messageId?: number; error?: string }> {
    if (!CHATWOOT_BASE_URL || !CHATWOOT_API_TOKEN) {
        logger.error("Missing CHATWOOT_BASE_URL or CHATWOOT_API_TOKEN");
        return { success: false, error: "Chatwoot not configured" };
    }

    const url = `${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}/messages`;

    try {
        logger.info({ conversationId }, "Sending message to Chatwoot");

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "api_access_token": CHATWOOT_API_TOKEN
            },
            body: JSON.stringify({
                content: message,
                message_type: "outgoing",
                private: false
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            logger.error({ status: response.status, error: errorText }, "Chatwoot API error");
            return { success: false, error: `API error: ${response.status}` };
        }

        const data = await response.json() as { id: number };
        logger.info({ messageId: data.id }, "Message sent to Chatwoot");

        return { success: true, messageId: data.id };
    } catch (error) {
        logger.error({ error }, "Chatwoot send error");
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
        };
    }
}

// ============================================
// Validate Webhook Payload
// ============================================

export function shouldProcessWebhook(payload: ChatwootWebhookPayload): {
    shouldProcess: boolean;
    reason?: string;
} {
    // Log full payload for debugging
    logger.debug({ event: payload.event, messageType: payload.message_type }, "Processing webhook");

    // Only process message_created events
    if (payload.event !== "message_created") {
        return { shouldProcess: false, reason: `Event type: ${payload.event}` };
    }

    // Only process incoming messages (from customers)
    if (payload.message_type !== "incoming") {
        return { shouldProcess: false, reason: `Message type: ${payload.message_type}` };
    }

    // Skip messages from agents or bots (but allow contacts and undefined)
    const senderType = payload.sender?.type;
    if (senderType === "user" || senderType === "agent_bot") {
        return { shouldProcess: false, reason: `Sender type: ${senderType}` };
    }

    // Skip conversations that are "open" (human agent is handling)
    const conversationStatus = payload.conversation?.status;
    if (conversationStatus === "open") {
        return { shouldProcess: false, reason: `Conversation status: ${conversationStatus} (human handling)` };
    }

    // Check for duplicate messages
    if (processedMessages.has(payload.id)) {
        return { shouldProcess: false, reason: "Duplicate message" };
    }

    // Mark as processed and schedule cleanup
    processedMessages.add(payload.id);
    setTimeout(() => processedMessages.delete(payload.id), MESSAGE_CACHE_TTL);

    return { shouldProcess: true };
}

// ============================================
// Extract Message Content
// ============================================

export function extractMessageContent(payload: ChatwootWebhookPayload): {
    text: string;
    attachments: ChatwootAttachment[];
    hasMedia: boolean;
    mediaTypes: string[];
} {
    const text = payload.content || "";
    const attachments = payload.attachments || [];
    const mediaTypes = attachments.map(a => a.file_type);

    return {
        text,
        attachments,
        hasMedia: attachments.length > 0,
        mediaTypes
    };
}

// ============================================
// Process Attachments
// Uses media.ts for audio transcription and image analysis
// ============================================

export async function processAttachments(
    attachments: ChatwootAttachment[]
): Promise<string> {
    // Process media attachments (audio, images) with AI
    const mediaResult = await processMediaAttachments(attachments);

    // Handle non-media attachments (location, etc)
    const parts: string[] = [];

    for (const attachment of attachments) {
        // Skip audio and image - already handled by processMediaAttachments
        if (attachment.file_type === "audio" || attachment.file_type === "image") {
            continue;
        }

        switch (attachment.file_type) {
            case "video":
                parts.push(`[Video adjunto - no puedo procesar videos. El usuario envió un video.]`);
                break;

            case "location":
                if (attachment.coordinates_lat && attachment.coordinates_long) {
                    parts.push(`[Ubicacion compartida: Lat ${attachment.coordinates_lat}, Long ${attachment.coordinates_long}]`);
                } else {
                    parts.push(`[Ubicacion compartida: ${attachment.fallback_title || "sin coordenadas"}]`);
                }
                break;

            case "file":
                parts.push(`[Archivo adjunto: ${attachment.extension || "documento"}]`);
                break;

            case "contact":
                parts.push(`[Contacto compartido]`);
                break;

            default:
                parts.push(`[Adjunto tipo: ${attachment.file_type}]`);
        }
    }

    // Combine media results with other attachments
    const allParts = [mediaResult, ...parts].filter(p => p.trim());
    return allParts.join("\n");
}

// ============================================
// Build Conversation Context
// ============================================

export function buildChatwootContext(payload: ChatwootWebhookPayload): {
    conversationId: string;
    accountId: number;
    chatwootConversationId: number;
    chatwootContactId: number | undefined;
    senderName: string;
    senderPhone?: string;
    senderEmail?: string;
    customAttributes?: Record<string, unknown>;
    inboxName: string;
    channel: string;
} {
    return {
        conversationId: `chatwoot-${payload.conversation.id}`,
        accountId: payload.account.id,
        chatwootConversationId: payload.conversation.id,
        chatwootContactId: payload.conversation.contact_id || payload.sender?.id,
        senderName: payload.sender?.name || "Usuario",
        senderPhone: payload.sender?.phone_number,
        senderEmail: payload.sender?.email || undefined,
        customAttributes: payload.sender?.custom_attributes,
        inboxName: payload.inbox?.name || "Unknown",
        channel: payload.conversation?.channel || "Unknown"
    };
}

// ============================================
// Update Conversation Status (Human Handoff)
// ============================================

export async function updateConversationStatus(
    accountId: number,
    conversationId: number,
    status: "open" | "pending" | "resolved" | "snoozed"
): Promise<{ success: boolean; error?: string }> {
    if (!CHATWOOT_BASE_URL || !CHATWOOT_API_TOKEN) {
        logger.error("Missing CHATWOOT_BASE_URL or CHATWOOT_API_TOKEN");
        return { success: false, error: "Chatwoot not configured" };
    }

    const url = `${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}`;

    try {
        logger.info({ conversationId, status }, "Updating conversation status");

        const response = await fetch(url, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "api_access_token": CHATWOOT_API_TOKEN
            },
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            const errorText = await response.text();
            logger.error({ status: response.status, error: errorText }, "Chatwoot status update error");
            return { success: false, error: `API error: ${response.status}` };
        }

        logger.info({ conversationId, status }, "Conversation status updated");
        return { success: true };
    } catch (error) {
        logger.error({ error }, "Chatwoot status update error");
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
        };
    }
}

// ============================================
// Health Check
// ============================================

export function getChatwootStatus(): {
    configured: boolean;
    baseUrl: string;
    hasToken: boolean;
} {
    return {
        configured: !!(CHATWOOT_BASE_URL && CHATWOOT_API_TOKEN),
        baseUrl: CHATWOOT_BASE_URL ? CHATWOOT_BASE_URL.replace(/\/+$/, "") : "not set",
        hasToken: !!CHATWOOT_API_TOKEN
    };
}
