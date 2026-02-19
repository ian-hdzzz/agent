/**
 * 11LabsCompanion - Main Entry Point
 * The ultimate ElevenLabs AI companion agent
 *
 * This agent uses Claude Agent SDK with skill-based routing
 * to intelligently manage all aspects of ElevenLabs:
 *
 * SKILLS:
 * - VOI (Voices): List, search, and manage voices
 * - AGT (Agents): Create and configure conversational AI agents
 * - TLS (Tools): Manage webhook tools for agents
 * - KNB (Knowledge): RAG knowledge base management
 * - AUD (Audio): Text-to-speech and audio generation
 * - CNV (Conversations): View and analyze conversation history
 * - ACC (Account): Subscription, usage, and phone numbers
 *
 * USAGE:
 * 1. Server mode: npm run server
 * 2. Direct import: import { runWorkflow } from './agent.js'
 */

import { config } from "dotenv";
config();

// Export main components
export { runWorkflow, getAgentHealth } from "./agent.js";
export { allTools } from "./tools.js";
export {
  SKILL_REGISTRY,
  getSkill,
  getAllSkills,
  getSkillDescriptions,
  classifyInput
} from "./skills/index.js";
export * from "./types.js";

// Interactive mode when run directly
async function main() {
  const { runWorkflow, getAgentHealth } = await import("./agent.js");

  console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     11LabsCompanion - ElevenLabs AI Assistant             ║
║                                                           ║
║     The ultimate companion for managing ElevenLabs        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
  `);

  const health = getAgentHealth();
  console.log(`Status: ${health.status}`);
  console.log(`Skills: ${health.skills.length}`);
  console.log(`API Key: ${process.env.ELEVENLABS_API_KEY ? '✓ Configured' : '✗ Missing'}\n`);

  // Check for command line arguments
  const args = process.argv.slice(2);

  if (args.length > 0) {
    // Run single query from command line
    const message = args.join(" ");
    console.log(`Query: ${message}\n`);

    const result = await runWorkflow({
      input_as_text: message
    });

    console.log("Response:");
    console.log(result.output_text);

    if (result.toolsUsed && result.toolsUsed.length > 0) {
      console.log(`\nTools used: ${result.toolsUsed.join(", ")}`);
    }
  } else {
    // Show help
    console.log("Usage:");
    console.log("  npm run dev -- \"your message here\"");
    console.log("  npm run server  # Start HTTP server");
    console.log("\nExamples:");
    console.log("  npm run dev -- \"list my voices\"");
    console.log("  npm run dev -- \"show my agents\"");
    console.log("  npm run dev -- \"check my subscription\"");
    console.log("  npm run dev -- \"create an agent named CustomerSupport\"");
  }
}

// Run if executed directly
main().catch(console.error);
