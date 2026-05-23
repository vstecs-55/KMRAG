# n8n Query Workflow Configuration Guide

This document provides the exact configuration for the nodes in the Query Workflow to ensure consistent implementation.

## 1. Webhook Node
- **HTTP Method**: `POST`
- **Path**: `line-query-webhook`
- **Response Mode**: `When Last Node Finishes`
- **Extraction (Expression)**:
    - `userId`: `{{ $json.body.events[0].source.userId }}`
    - `text`: `{{ $json.body.events[0].message.text }}`

## 2. Memory Retrieval Node (HTTP Request / Execute Command)
- **Method**: `Execute Command`
- **Command**:
  ```bash
  sqlite3 "/home/admin/Documents/Projects/KM RAG/chat_history.db" "SELECT role, content FROM history WHERE user_id='{{ $json.userId }}' ORDER BY timestamp DESC LIMIT 5;"
  ```
- **Post-processing**: Use a `Code` node to convert the SQLite output into a JSON array of messages.

## 3. Intent Router Node (HTTP Request)
- **Method**: `POST`
- **URL**: `http://localhost:11434/api/chat`
- **Authentication**: `None`
- **Body Parameters (JSON)**:
    - `model`: `llama3.3:70b`
    - `messages`:
      ```json
      [
        { "role": "system", "content": "คุณคือผู้เชี่ยวชาญในการวิเคราะห์เจตนา... (see query_workflow_spec.md)" },
        {{ $node["Memory Retrieval"].json.history }},
        { "role": "user", "content": "{{ $node["Webhook"].json.text }}" }
      ]
      ```
    - `stream`: `false`
    - `format`: `json`

## 4. Switch Node
- **Data Type**: `String`
- **Value to Test**: `{{ $json.message.content.intent_type }}`
- **Routing Rules**:
    - `Technical Spec` $\rightarrow$ Route to Technical RAG
    - `Pricing/Quantity` $\rightarrow$ Route to Pricing/Inventory RAG
    - `Visual/Architecture` $\rightarrow$ Route to Visual/Asset RAG
    - `General/Greeting` $\rightarrow$ Route to Greeting/General Flow

## Testing the Webhook
You can simulate a Line webhook request using the following `curl` command:

```bash
curl -X POST http://localhost:5678/webhook/line-query-webhook \
-H "Content-Type: application/json" \
-d '{
  "events": [
    {
      "source": { "userId": "test_user_123" },
      "message": { "text": "ราคา EPYC เท่าไหร่ครับ" }
    }
  ]
}'
```
