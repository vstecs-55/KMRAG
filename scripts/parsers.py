import os
import sys
import argparse
import pandas as pd
import pdfplumber
from docx import Document

def parse_excel(file_path):
    """
    Reads an Excel file and converts it to a Markdown table.
    """
    try:
        # Read the excel file. By default, it reads the first sheet.
        df = pd.read_excel(file_path)
        # Convert to markdown table using to_markdown() which uses tabulate under the hood.
        return df.to_markdown(index=False)
    except Exception as e:
        return f"Error parsing Excel file {file_path}: {str(e)}"

def semantic_chunking(text, chunk_size=1000, overlap=200):
    """
    Splits text into chunks based on logical sections (double newlines)
    and maintains a context window (overlap).
    """
    # Split by double newlines to identify logical sections
    sections = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # If adding this section exceeds chunk_size, we start a new chunk
        if len(current_chunk) + len(section) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)

            # Start new chunk with overlap from the end of the previous chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + section
        else:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def parse_pdf(file_path):
    """
    Reads a PDF file and applies semantic chunking.
    """
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

        chunks = semantic_chunking(text)
        return "\n\n---CHUNK---\n\n".join(chunks)
    except Exception as e:
        return f"Error parsing PDF file {file_path}: {str(e)}"

def parse_word(file_path):
    """
    Reads a Word file and applies semantic chunking.
    """
    try:
        doc = Document(file_path)
        text = "\n\n".join([para.text for para in doc.paragraphs])

        chunks = semantic_chunking(text)
        return "\n\n---CHUNK---\n\n".join(chunks)
    except Exception as e:
        return f"Error parsing Word file {file_path}: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Advanced Text Parsers for RAG")
    parser.add_argument("file_path", help="Path to the file to be parsed")
    args = parser.parse_args()

    file_path = args.file_path
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.xlsx', '.xls']:
        result = parse_excel(file_path)
    elif ext == '.pdf':
        result = parse_pdf(file_path)
    elif ext == '.docx':
        result = parse_word(file_path)
    else:
        print(f"Unsupported file extension: {ext}")
        sys.exit(1)

    print(result)

if __name__ == "__main__":
    main()
