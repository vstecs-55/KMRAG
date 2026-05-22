# Ingestion Workflow Specification

## Overview
The Ingestion Workflow is the entry point for the KM RAG pipeline. It monitors a local directory for new files and routes them to the appropriate processing pipeline based on their file extension.

## Trigger
- **Trigger Type**: Local File Trigger (or Cron scanning the directory).
- **Monitored Directory**: `/home/admin/Documents/Projects/KM RAG/Database`
- **Event**: New file created or updated.

## Routing Logic
The workflow uses a 'Switch' node to determine the processing path based on the file extension.

### Routing Rules
| File Extension | Target Route | Description |
|----------------|--------------|-------------|
| `.pdf`         | PDF Route    | Extracts text and metadata from PDF files |
| `.docx`        | DOCX Route   | Extracts text and metadata from Word documents |
| `.xlsx`        | XLSX Route   | Processes spreadsheet data |
| `.pptx`        | PPTX Route   | Extracts text from PowerPoint presentations |
| `.png`         | Image Route  | Performs OCR or image analysis |
| `.jpg`         | Image Route  | Performs OCR or image analysis |
| Other          | Default Route| Logs unsupported file type |

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
