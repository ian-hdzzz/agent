#!/usr/bin/env node

import { Command } from "commander";
import chalk from "chalk";
import ora from "ora";
import { readInput, getProcessNameFromFile } from "./utils/file-io.js";
import { runPipeline } from "./pipeline.js";
import { extractMermaidCode, wrapMermaidBlock } from "./utils/mermaid.js";
import { join, resolve } from "path";
import { readdirSync, statSync, readFileSync, writeFileSync, existsSync } from "fs";
import type { ModelAlias, ProgressCallback } from "./types.js";

const program = new Command();

program
  .name("process-builder")
  .description(
    "Herramienta de mapeo y optimización de trámites gubernamentales para la transformación digital de México"
  )
  .version("2.0.0");

// ═══════════════════════════════════════════════════════════════════
// ANALYZE command
// ═══════════════════════════════════════════════════════════════════
program
  .command("analyze")
  .description(
    "Analiza un trámite y genera documentación AS-IS + TO-BE optimizado con auditoría de cumplimiento"
  )
  .requiredOption(
    "-i, --input <files...>",
    "Archivo(s) con la descripción del trámite (TXT, PDF, imágenes)"
  )
  .option("-n, --name <name>", "Nombre del trámite")
  .option("-d, --department <dept>", "Secretaría o dependencia", "Sin especificar")
  .option("-o, --output <dir>", "Directorio de salida", "./output")
  .option(
    "--model <model>",
    "Modelo de Claude: sonnet (default), opus, haiku",
    "sonnet"
  )
  .option("--no-thinking", "Deshabilitar extended thinking")
  .option("--skip-compliance", "Omitir auditoría de cumplimiento")
  .option("--skip-implementation", "Omitir plan de implementación")
  .option("--push-to-paco", "Enviar resultados a PACO API")
  .option("--paco-url <url>", "URL de la API de PACO")
  .option("--paco-token <token>", "Token de autenticación de PACO")
  .action(async (opts) => {
    printBanner();

    // Validate model
    const validModels = ["sonnet", "opus", "haiku"];
    if (!validModels.includes(opts.model)) {
      console.error(
        chalk.red(
          `Error: Modelo inválido "${opts.model}". Opciones: ${validModels.join(", ")}`
        )
      );
      process.exit(1);
    }

    // Validate input files exist
    for (const file of opts.input) {
      if (!existsSync(file)) {
        console.error(chalk.red(`Error: Archivo no encontrado: ${file}`));
        process.exit(1);
      }
    }

    const processName =
      opts.name || getProcessNameFromFile(opts.input[0]);
    const department = opts.department;
    const outputBaseDir = join(process.cwd(), opts.output);

    // Resolve PACO settings from flags or env
    const pushToPaco = opts.pushToPaco || false;
    const pacoUrl = opts.pacoUrl || process.env.PACO_API_URL;
    const pacoToken = opts.pacoToken || process.env.PACO_API_TOKEN;

    if (pushToPaco && (!pacoUrl || !pacoToken)) {
      console.error(
        chalk.red(
          "Error: --push-to-paco requiere --paco-url y --paco-token (o variables de entorno PACO_API_URL y PACO_API_TOKEN)"
        )
      );
      process.exit(1);
    }

    console.log(chalk.gray(`Trámite:      ${chalk.white(processName)}`));
    console.log(chalk.gray(`Dependencia:  ${chalk.white(department)}`));
    console.log(
      chalk.gray(`Entrada:      ${chalk.white(opts.input.join(", "))}`)
    );
    console.log(chalk.gray(`Salida:       ${chalk.white(outputBaseDir)}`));
    console.log(chalk.gray(`Modelo:       ${chalk.white(opts.model)}`));
    console.log(
      chalk.gray(
        `Thinking:     ${chalk.white(opts.thinking !== false ? "habilitado" : "deshabilitado")}`
      )
    );
    if (opts.skipCompliance)
      console.log(chalk.gray(`Compliance:   ${chalk.yellow("omitido")}`));
    if (opts.skipImplementation)
      console.log(chalk.gray(`Implementación: ${chalk.yellow("omitido")}`));
    if (pushToPaco)
      console.log(chalk.gray(`PACO:         ${chalk.cyan(pacoUrl)}`));
    console.log();

    const spinners = new Map<string, ReturnType<typeof ora>>();

    const onProgress: ProgressCallback = (stage, status, detail) => {
      if (status === "start") {
        const spinner = ora({
          text: chalk.cyan(stage),
          prefixText: "  ",
        }).start();
        spinners.set(stage, spinner);
      } else if (status === "done") {
        const spinner = spinners.get(stage);
        if (spinner) {
          spinner.succeed(chalk.green(stage));
        }
      } else if (status === "error" || status === "warn") {
        const spinner = spinners.get(stage);
        if (spinner) {
          spinner.warn(chalk.yellow(`${stage} — ${detail || "advertencia"}`));
        }
      }
    };

    try {
      const result = await runPipeline(
        {
          inputFiles: opts.input,
          processName,
          department,
          outputBaseDir,
          model: opts.model as ModelAlias,
          thinkingEnabled: opts.thinking !== false,
          skipCompliance: opts.skipCompliance || false,
          skipImplementation: opts.skipImplementation || false,
          pushToPaco,
          pacoUrl,
          pacoToken,
        },
        onProgress
      );

      // Print summary
      console.log(
        chalk.bold.green("\n✓ Análisis completado exitosamente\n")
      );
      console.log(chalk.gray("Archivos generados:"));
      for (const file of result.files) {
        console.log(chalk.white(`  → ${file}`));
      }

      const durationSec = (result.metadata.totalDurationMs / 1000).toFixed(1);
      const totalTokens =
        result.metadata.totalTokens.inputTokens +
        result.metadata.totalTokens.outputTokens;

      console.log(
        chalk.gray(
          `\nDuración total: ${chalk.white(durationSec + "s")} | Tokens: ${chalk.white(totalTokens.toLocaleString())}`
        )
      );

      if (result.metadata.failedAgents.length > 0) {
        console.log(
          chalk.yellow(
            `\nAgentes con error: ${result.metadata.failedAgents.join(", ")}`
          )
        );
      }

      console.log(
        chalk.gray(
          `\nDirectorio de salida: ${chalk.white(result.outputDir)}`
        )
      );
      console.log();
    } catch (err: any) {
      for (const spinner of spinners.values()) {
        spinner.fail();
      }
      console.error(chalk.red(`\nError fatal: ${err.message}`));
      if (err.message.includes("ANTHROPIC_API_KEY")) {
        console.error(
          chalk.yellow(
            "Asegúrate de configurar tu ANTHROPIC_API_KEY en las variables de entorno."
          )
        );
      }
      process.exit(1);
    }
  });

// ═══════════════════════════════════════════════════════════════════
// BATCH command
// ═══════════════════════════════════════════════════════════════════
program
  .command("batch")
  .description("Procesa múltiples trámites desde un directorio")
  .requiredOption(
    "-d, --dir <directory>",
    "Directorio con archivos de trámites"
  )
  .option("-o, --output <dir>", "Directorio de salida", "./output")
  .option(
    "--model <model>",
    "Modelo de Claude: sonnet (default), opus, haiku",
    "sonnet"
  )
  .option("--no-thinking", "Deshabilitar extended thinking")
  .option("-c, --concurrency <n>", "Trámites simultáneos", "1")
  .option("--skip-compliance", "Omitir auditoría de cumplimiento")
  .option("--skip-implementation", "Omitir plan de implementación")
  .action(async (opts) => {
    printBanner();

    const dir = resolve(opts.dir);
    if (!existsSync(dir)) {
      console.error(chalk.red(`Error: Directorio no encontrado: ${dir}`));
      process.exit(1);
    }

    const files = readdirSync(dir).filter((f) =>
      /\.(txt|md|pdf|png|jpg|jpeg)$/i.test(f)
    );

    if (files.length === 0) {
      console.error(
        chalk.yellow(
          "No se encontraron archivos soportados (.txt, .md, .pdf, .png, .jpg) en el directorio."
        )
      );
      process.exit(1);
    }

    console.log(
      chalk.gray(`Encontrados ${chalk.white(files.length.toString())} archivo(s) para procesar`)
    );
    console.log(
      chalk.gray(`Concurrencia: ${chalk.white(opts.concurrency)}`)
    );
    console.log();

    const concurrency = Math.max(1, parseInt(opts.concurrency, 10) || 1);
    let completed = 0;
    let failed = 0;

    // Process in batches
    for (let i = 0; i < files.length; i += concurrency) {
      const batch = files.slice(i, i + concurrency);
      const promises = batch.map(async (file) => {
        const filePath = join(dir, file);
        const processName = getProcessNameFromFile(file);
        console.log(
          chalk.cyan(`  Procesando: ${processName} (${file})`)
        );

        try {
          await runPipeline({
            inputFiles: [filePath],
            processName,
            department: "Sin especificar",
            outputBaseDir: join(process.cwd(), opts.output),
            model: opts.model as ModelAlias,
            thinkingEnabled: opts.thinking !== false,
            skipCompliance: opts.skipCompliance || false,
            skipImplementation: opts.skipImplementation || false,
            pushToPaco: false,
          });
          completed++;
          console.log(
            chalk.green(`  ✓ ${processName}`)
          );
        } catch (err: any) {
          failed++;
          console.error(
            chalk.red(`  ✗ ${processName}: ${err.message}`)
          );
        }
      });

      await Promise.allSettled(promises);
    }

    console.log(
      chalk.bold(
        `\nResultados: ${chalk.green(completed + " completados")}, ${chalk.red(failed + " fallidos")} de ${files.length} total`
      )
    );
  });

// ═══════════════════════════════════════════════════════════════════
// DIAGRAM command
// ═══════════════════════════════════════════════════════════════════
program
  .command("diagram")
  .description("Regenera diagramas a partir de un análisis existente")
  .requiredOption(
    "-i, --input <file>",
    "Archivo markdown con el análisis (AS-IS o TO-BE)"
  )
  .option(
    "-t, --type <type>",
    "Tipo de diagrama: as-is, to-be-digital, to-be-hybrid",
    "as-is"
  )
  .option("-o, --output <file>", "Archivo de salida .mmd")
  .option(
    "--model <model>",
    "Modelo de Claude: sonnet (default), opus, haiku",
    "sonnet"
  )
  .action(async (opts) => {
    const validTypes = ["as-is", "to-be-digital", "to-be-hybrid"];
    if (!validTypes.includes(opts.type)) {
      console.error(
        chalk.red(
          `Error: Tipo inválido "${opts.type}". Opciones: ${validTypes.join(", ")}`
        )
      );
      process.exit(1);
    }

    const inputPath = resolve(opts.input);
    if (!existsSync(inputPath)) {
      console.error(chalk.red(`Error: Archivo no encontrado: ${inputPath}`));
      process.exit(1);
    }

    const spinner = ora("Generando diagrama...").start();

    try {
      const { default: Anthropic } = await import("@anthropic-ai/sdk");
      const {
        DIAGRAM_AS_IS_PROMPT,
        DIAGRAM_TO_BE_PROMPT,
      } = await import("./prompts/diagram-generator.js");

      const client = new Anthropic();
      const model =
        opts.model in
        { sonnet: 1, opus: 1, haiku: 1 }
          ? ({
              sonnet: "claude-sonnet-4-5-20250929",
              opus: "claude-opus-4-6",
              haiku: "claude-haiku-4-5-20251001",
            } as Record<string, string>)[opts.model]
          : "claude-sonnet-4-5-20250929";

      const sourceText = readFileSync(inputPath, "utf-8");
      const systemPrompt =
        opts.type === "as-is" ? DIAGRAM_AS_IS_PROMPT : DIAGRAM_TO_BE_PROMPT;

      let userText = sourceText;
      if (opts.type === "to-be-hybrid") {
        userText =
          "INSTRUCCIÓN ESPECIAL: Genera el diagrama para el ESCENARIO HÍBRIDO/PAPEL del proceso optimizado.\n\n" +
          sourceText;
      }

      const response = await client.messages.create({
        model,
        max_tokens: 8000,
        system: systemPrompt,
        messages: [{ role: "user", content: userText }],
      });

      const block = response.content[0];
      if (block.type !== "text") {
        throw new Error("Respuesta inesperada del modelo");
      }

      const mermaidCode = extractMermaidCode(block.text);
      const outputPath =
        opts.output || inputPath.replace(/\.md$/, `.${opts.type}.mmd`);
      writeFileSync(outputPath, mermaidCode, "utf-8");

      spinner.succeed(
        chalk.green(`Diagrama generado: ${outputPath}`)
      );
    } catch (err: any) {
      spinner.fail(chalk.red(`Error: ${err.message}`));
      process.exit(1);
    }
  });

// ═══════════════════════════════════════════════════════════════════
// LIST command
// ═══════════════════════════════════════════════════════════════════
program
  .command("list")
  .description("Lista los análisis generados previamente")
  .option("-o, --output <dir>", "Directorio de salida", "./output")
  .action(async (opts) => {
    const outputDir = join(process.cwd(), opts.output);

    try {
      const entries = readdirSync(outputDir);
      if (entries.length === 0) {
        console.log(chalk.yellow("No hay análisis generados aún."));
        return;
      }

      console.log(chalk.bold("\nAnálisis generados:\n"));
      for (const entry of entries.sort().reverse()) {
        const stat = statSync(join(outputDir, entry));
        if (stat.isDirectory()) {
          const date = entry.slice(0, 10);
          const name = entry.slice(11).replace(/-/g, " ");

          // Check for metadata.json
          const metadataPath = join(outputDir, entry, "metadata.json");
          let modelInfo = "";
          if (existsSync(metadataPath)) {
            try {
              const metadata = JSON.parse(
                readFileSync(metadataPath, "utf-8")
              );
              modelInfo = ` ${chalk.gray(`[${metadata.model}]`)}`;
            } catch {
              // ignore
            }
          }

          console.log(
            `  ${chalk.gray(date)}  ${chalk.white(name)}${modelInfo}`
          );
        }
      }
      console.log();
    } catch {
      console.log(
        chalk.yellow("No se encontró el directorio de salida.")
      );
    }
  });

program.parse();

// ─── Helpers ──────────────────────────────────────────────────────

function printBanner(): void {
  console.log(
    chalk.bold.blue(
      "\n╔══════════════════════════════════════════════════════════╗"
    )
  );
  console.log(
    chalk.bold.blue(
      "║       PROCESS BUILDER v2.0 - Transformación Digital     ║"
    )
  );
  console.log(
    chalk.bold.blue(
      "║   Mapeo y Optimización de Trámites Gubernamentales      ║"
    )
  );
  console.log(
    chalk.bold.blue(
      "║   6 Agentes · Extended Thinking · Multi-archivo          ║"
    )
  );
  console.log(
    chalk.bold.blue(
      "╚══════════════════════════════════════════════════════════╝\n"
    )
  );
}
