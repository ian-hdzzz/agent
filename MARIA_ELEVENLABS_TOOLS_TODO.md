# Maria ElevenLabs Tools - COMPLETED

## Summary

Maria voice agent is now fully configured with webhook tools that connect to the CEA Querétaro backend.

## Completed Steps

### 1. Deployed maria-voz to GCP Server
- [x] Synced code to `/home/fcamacholombardo/maria-voz/`
- [x] Installed dependencies
- [x] Created `.env` file with database credentials
- [x] Started with PM2: `pm2 start ecosystem.config.cjs`
- [x] Opened firewall port 3003: `gcloud compute firewall-rules create allow-maria-voz --allow tcp:3003`

### 2. Created 6 Webhook Tools
| Tool Name | Tool ID | URL |
|-----------|---------|-----|
| `consultar_saldo` | `tool_3101kggepz73fecvskht2t8p1m4y` | `http://34.122.65.54:3003/webhook/consultar_saldo` |
| `consultar_consumo` | `tool_5601kggeq1cqfq2t5czc82tpsd2c` | `http://34.122.65.54:3003/webhook/consultar_consumo` |
| `consultar_contrato` | `tool_6901kggeq31rf9ys904s3sw9tze1` | `http://34.122.65.54:3003/webhook/consultar_contrato` |
| `consultar_tickets` | `tool_2301kggeq4dveprbmqhm7gz4dg7m` | `http://34.122.65.54:3003/webhook/consultar_tickets` |
| `crear_reporte` | `tool_8801kggeq99jfay8k8dqrq85afhd` | `http://34.122.65.54:3003/webhook/crear_reporte` |
| `transferir_humano` | `tool_6701kggeqaejffhr9frq0p2jj5q2` | `http://34.122.65.54:3003/webhook/transferir_humano` |

### 3. Updated Maria Agent
- [x] Agent ID: `agent_7301kg0z72effkvtqghs2hx58bpt`
- [x] Name: "Maria CEA"
- [x] Language: Spanish
- [x] First message: "Hola, soy María de CEA Querétaro. ¿En qué puedo ayudarte?"
- [x] System prompt: Voice-optimized Spanish prompt
- [x] Voice: Cristina Campos (Mexican, conversational)
- [x] All 6 tools attached

### 4. Verified Everything Works
- [x] Health check: `curl http://34.122.65.54:3003/health`
- [x] Tool test: `curl -X POST http://34.122.65.54:3003/webhook/consultar_saldo -H "Content-Type: application/json" -d '{"contrato": "523160"}'`

## Server Info

- **GCP Server**: `34.122.65.54`
- **maria-voz Port**: 3003
- **PM2 Process**: `maria-voz`

## Testing Maria

You can test Maria at: https://elevenlabs.io/app/conversational-ai

Or call the SIP trunk: `mariacea.sip.twilio.com`

## Architecture

```
User Call → Twilio SIP → ElevenLabs Maria Agent
                              ↓
                         LLM decides tool
                              ↓
                         Tool webhook call
                              ↓
           maria-voz (34.122.65.54:3003) ← CEA API / Database
                              ↓
                         Response to LLM
                              ↓
                    Maria speaks response
```
