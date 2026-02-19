# AGORA-5 Transfer Handler Changes for Maria CEA Voice Transfer

These changes need to be applied to AGORA-5 on the GCP server to handle SIP transfers from Maria CEA voice agent.

## File: `app/services/twilio_voice/transfer_handler.rb`

Add the following methods to the `TwilioVoice::TransferHandler` class:

### 1. Extract SIP Headers from Twilio Params

```ruby
def extract_transfer_context(params)
  # Twilio passes SIP headers as SipHeader_X-* params
  {
    transferred_from: params['SipHeader_X-Transfer-Source'] || 'maria-cea',
    intent: params['SipHeader_X-Intent'],
    transfer_notes: params['SipHeader_X-Transfer-Notes'],
    contract: params['SipHeader_X-Contract'],
    customer_name: params['SipHeader_X-Customer-Name'],
    transfer_call_sid: params['CallSid'],
    transferred_at: Time.current.iso8601
  }.compact
end
```

### 2. Create Context Note in Conversation

```ruby
def create_transfer_context_note(conversation, context)
  return if context[:intent].blank? && context[:transfer_notes].blank?

  conversation.messages.create!(
    account: conversation.account,
    inbox: conversation.inbox,
    message_type: :activity,
    private: true,  # Only visible to agents in conversation window
    content: build_context_notes(context)
  )
end

def build_context_notes(context)
  notes = ["📞 **Transferencia de María (Voz)**", ""]
  notes << "**Cliente**: #{context[:customer_name]}" if context[:customer_name].present?
  notes << "**Contrato**: #{context[:contract]}" if context[:contract].present?
  notes << "**Intent**: #{context[:intent]}" if context[:intent].present?
  if context[:transfer_notes].present?
    notes << ""
    notes << "**Notas**:"
    notes << context[:transfer_notes]
  end
  notes << ""
  notes << "_Contexto automático de la conversación con María_"
  notes.join("\n")
end
```

### 3. Update `handle_bot_transfer` Method

In the existing `handle_bot_transfer` method, add after creating the voice_call:

```ruby
def handle_bot_transfer(customer_phone:, call_sid:, transfer_to: nil, params: {})
  # ... existing code to find/create contact and conversation ...

  # Create voice call with transfer context from SIP headers
  transfer_context = extract_transfer_context(params)

  voice_call = VoiceCall.create!(
    conversation: @conversation,
    # ... other existing fields ...
    transfer_context: transfer_context  # Store SIP header data
  )

  # Add private note with context to the conversation
  create_transfer_context_note(@conversation, transfer_context)

  # ... rest of existing code ...
end
```

## File: `app/controllers/twilio_voice/webhooks_controller.rb`

Ensure the transfer webhook passes all params including SIP headers:

```ruby
def transfer
  # Ensure we pass all params to the handler for SIP header extraction
  result = TwilioVoice::TransferHandler.new(
    account: current_account,
    inbox: @inbox
  ).handle_bot_transfer(
    customer_phone: params[:From],
    call_sid: params[:CallSid],
    transfer_to: params[:To],
    params: params.to_unsafe_h  # Pass all params for SIP header extraction
  )

  # ... rest of method ...
end
```

## Twilio Configuration

### Configure +14159174609 Webhook

In Twilio Console, set the voice webhook for +14159174609 to detect Maria transfers:

**Option 1**: Create a TwiML Bin that checks for SIP headers and routes accordingly:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <!-- If X-Transfer-Source header present, route to transfer endpoint -->
  <!-- Otherwise route to normal voice endpoint -->
  <Redirect method="POST">
    https://your-agora-domain.com/twilio_voice/webhooks/transfer?phone=14159174609
  </Redirect>
</Response>
```

**Option 2**: Route ALL calls to the transfer endpoint and let AGORA detect the context:
- Voice URL: `https://your-agora-domain.com/twilio_voice/webhooks/transfer?phone=14159174609`

## ElevenLabs Agent Configuration

### 1. Dynamic Variables

Add these dynamic variables in ElevenLabs Dashboard → Agent → Dynamic Variables:

| Variable | Description |
|----------|-------------|
| `intent` | Customer's current intent (set by tool responses) |
| `transfer_notes` | Summary notes for transfer (set by tool responses) |
| `contrato` | Contract number (set by consultar_* tools) |
| `customer_name` | Customer/titular name (set by consultar_contrato tool) |

### 2. Transfer System Tool Configuration

Add `transfer_to_number` system tool with custom SIP headers:

```json
{
  "transfers": [{
    "transfer_destination": {
      "type": "phone_number",
      "phone_number": "+14159174609"
    },
    "condition": "when user requests a human agent",
    "transfer_type": "sip_refer",
    "client_message": "Te comunico con un asesor. Un momento por favor.",
    "agent_message": "Transferencia de Maria",
    "custom_sip_headers": [
      { "key": "X-Transfer-Source", "value": "maria-cea" },
      { "key": "X-Intent", "value": "{{intent}}" },
      { "key": "X-Transfer-Notes", "value": "{{transfer_notes}}" },
      { "key": "X-Contract", "value": "{{contrato}}" },
      { "key": "X-Customer-Name", "value": "{{customer_name}}" }
    ]
  }]
}
```

## Expected Agent Experience

When a call is transferred from Maria, the agent sees in the conversation:

```
📞 Incoming call from +524423463572
   Duration: 2:50

🔒 Private Note
────────────────────────────────────────────
📞 **Transferencia de María (Voz)**

**Cliente**: Juan Pérez García
**Contrato**: 523160
**Intent**: consulta_saldo

**Notas**:
Consultó saldo: $2,500 (vencido: $1,200, por vencer: $1,300)
Transferido a humano: necesita convenio de pago

_Contexto automático de la conversación con María_
────────────────────────────────────────────
```

## Testing Checklist

1. [ ] Call Maria CEA, use tools (consultar_saldo, consultar_contrato)
2. [ ] Say "quiero hablar con un humano"
3. [ ] Verify SIP REFER is sent with X-* headers in Twilio logs
4. [ ] Verify AGORA receives SipHeader_X-* params in webhook
5. [ ] Verify conversation has private note with context
6. [ ] Verify agent can see the context notes
