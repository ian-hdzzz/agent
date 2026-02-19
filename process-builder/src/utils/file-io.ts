import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, basename, extname } from "path";
import type { ExtractedFile, PipelineMetadata } from "../types.js";

// ─── Existing utilities (preserved) ─────────────────────────────

export function readInput(filePath: string): string {
  if (!existsSync(filePath)) {
    throw new Error(`Archivo no encontrado: ${filePath}`);
  }
  return readFileSync(filePath, "utf-8");
}

export function ensureOutputDir(outputDir: string): void {
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
  }
}

export function writeMarkdown(
  outputDir: string,
  filename: string,
  content: string
): string {
  ensureOutputDir(outputDir);
  const filePath = join(outputDir, filename);
  writeFileSync(filePath, content, "utf-8");
  return filePath;
}

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function buildOutputDir(
  baseDir: string,
  processName: string
): string {
  const slug = slugify(processName);
  const timestamp = new Date().toISOString().slice(0, 10);
  return join(baseDir, `${timestamp}_${slug}`);
}

export function getProcessNameFromFile(filePath: string): string {
  const name = basename(filePath, extname(filePath));
  return name
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── New utilities for multi-file support ────────────────────────

/**
 * MIME type detection based on file extension.
 */
const MIME_MAP: Record<string, string> = {
  ".txt": "text/plain",
  ".md": "text/markdown",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".bmp": "image/bmp",
  ".csv": "text/csv",
};

function getMimeType(filePath: string): string {
  const ext = extname(filePath).toLowerCase();
  return MIME_MAP[ext] || "application/octet-stream";
}

function isTextFile(mimeType: string): boolean {
  return mimeType.startsWith("text/");
}

function isImageFile(mimeType: string): boolean {
  return mimeType.startsWith("image/");
}

function isPdfFile(mimeType: string): boolean {
  return mimeType === "application/pdf";
}

/**
 * Read a file and return its content with metadata.
 * Text files are read as UTF-8. Binary files are read as base64.
 */
export function readFileForExtraction(filePath: string): ExtractedFile {
  if (!existsSync(filePath)) {
    throw new Error(`Archivo no encontrado: ${filePath}`);
  }

  const mimeType = getMimeType(filePath);
  const buffer = readFileSync(filePath);

  let content: string;
  if (isTextFile(mimeType)) {
    content = buffer.toString("utf-8");
  } else {
    content = buffer.toString("base64");
  }

  return {
    filename: basename(filePath),
    mimeType,
    sizeBytes: buffer.length,
    content,
  };
}

/**
 * Build Anthropic content blocks for a file (for the document extractor agent).
 * - Text files → text content block
 * - Images → image content block (base64)
 * - PDFs → document content block (base64)
 */
export function buildContentBlocksForFile(
  file: ExtractedFile
): Array<{ type: string; [key: string]: any }> {
  if (isTextFile(file.mimeType)) {
    return [
      {
        type: "text",
        text: `--- Archivo: ${file.filename} (${file.mimeType}, ${file.sizeBytes} bytes) ---\n\n${file.content}`,
      },
    ];
  }

  if (isImageFile(file.mimeType)) {
    return [
      {
        type: "text",
        text: `--- Archivo: ${file.filename} (${file.mimeType}, ${file.sizeBytes} bytes) ---`,
      },
      {
        type: "image",
        source: {
          type: "base64",
          media_type: file.mimeType,
          data: file.content,
        },
      },
    ];
  }

  if (isPdfFile(file.mimeType)) {
    return [
      {
        type: "text",
        text: `--- Archivo: ${file.filename} (${file.mimeType}, ${file.sizeBytes} bytes) ---`,
      },
      {
        type: "document",
        source: {
          type: "base64",
          media_type: file.mimeType,
          data: file.content,
        },
      },
    ];
  }

  // Fallback: try as text
  return [
    {
      type: "text",
      text: `--- Archivo: ${file.filename} (${file.mimeType}, ${file.sizeBytes} bytes) ---\n[Formato no soportado directamente. Contenido base64 omitido.]`,
    },
  ];
}

/**
 * Write the pipeline metadata as JSON.
 */
export function writeMetadata(
  outputDir: string,
  metadata: PipelineMetadata
): string {
  ensureOutputDir(outputDir);
  const filePath = join(outputDir, "metadata.json");
  writeFileSync(filePath, JSON.stringify(metadata, null, 2), "utf-8");
  return filePath;
}

/**
 * Write a file to a subdirectory (e.g., diagramas/).
 */
export function writeToSubdir(
  outputDir: string,
  subdir: string,
  filename: string,
  content: string
): string {
  const dir = join(outputDir, subdir);
  ensureOutputDir(dir);
  const filePath = join(dir, filename);
  writeFileSync(filePath, content, "utf-8");
  return filePath;
}
