# Ingestion Workflow Specification

## Overview
The Ingestion Workflow is the entry point for the KM RAG pipeline. It monitors a local directory for new files and routes them to the appropriate processing pipeline based on their file extension.

## Trigger
- **Trigger Type**: Local File Trigger (Polling-based).
- **Monitored Directory**: `/home/admin/Documents/Projects/KM RAG/Database`
- **Event**: New file created or updated.

## Routing Logic
The workflow uses a 'Switch' node to determine the processing path based on the file extension.

### Routing Rules
| File Extension | Target Route | Description |
|----------------|--------------|-------------|
| `.pdf`         | PDF Route    | Extracts text and metadata from PDF files |
| `.docx`        | DOCX Route   | Extracts text and metadata from Word documents |
| `.xlsx`, `.csv`| Spreadsheet Route| Processes spreadsheet and CSV data |
| `.pptx`        | PPTX Route   | Extracts text from PowerPoint presentations |
| `.png`, `.jpg`, `.jpeg`| Image Route  | Performs OCR or image analysis via Ollama |
| `.txt`, `.md`  | Text Route   | Direct text extraction |
| Other          | Default Route| Logs unsupported file type |

## Extension Extraction Logic
The file extension is extracted from the filename using a JavaScript expression in a Code node or within the Switch node's expression editor:
`{{ $json.fileName.split('.').pop().toLowerCase() }}`
This ensures that the routing is case-insensitive and correctly identifies the trailing extension.

## Route Details

### Image Route
The Image Route integrates Ollama (Llama 3.2 Vision) to transform visual content into detailed technical descriptions.

- **Node**: HTTP Request
- **Endpoint**: `http://localhost:11434/api/generate`
- **Method**: POST
- **Authentication**: None
- **Payload**:
  ```json
  {
    "model": "llama3.2-vision:11b",
    "prompt": "Describe this technical diagram or image in extreme detail for a knowledge base. Focus on labels, components, connections, and the overall architecture. Convert visual information into a structured textual description.",
    "stream": false,
    "images": ["<base64_image_data>"]
  }
  ```
- **Image Handling**: The binary data from the "Read File" node is converted to a Base64 string before being inserted into the `images` array of the payload.
- **Output**: The response is a JSON object containing a `response` field with the textual description.

## Error Handling
- **Unsupported Formats**: Files falling into the "Default Route" are logged to a `rejected_files.log` file in the project root, including the timestamp and full filename.
- **Read File Failures**: The "Read File" node is configured with "On Error: Continue". A subsequent filter node checks if the file content is empty or if an error property is present, routing failures to an error notification channel to prevent workflow crashes.

## Workflow Flow
1. **Trigger** $\rightarrow$ Detects file in `/home/admin/Documents/Projects/KM RAG/Database`.
2. **Read File** $\rightarrow$ Reads the file binary/metadata.
3. **Switch Node** $\rightarrow$ Evaluates `{{ $json.extension }}`.
4. **Target Routes** $\rightarrow$ Sends the file to the corresponding handler.

## Verification Plan
1. Place a `.pdf` file in the `Database/` folder.
2. Verify the workflow triggers.
3. Verify the file reaches the "PDF Route" in the Switch node.
4. Repeat for other supported extensions.
