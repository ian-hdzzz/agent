// ============================================
// Maria V3 - Entry Point
// ============================================

import { config } from "dotenv";
config();

import { startServer } from "./server.js";
import { logger } from "./utils/logger.js";

// Banner
console.log(`
╔═══════════════════════════════════════════════╗
║                 MARIA V3                       ║
║    CEA Querétaro - AI Customer Service         ║
║                                                ║
║  Combined architecture from:                   ║
║  - maria-v2 (infrastructure)                   ║
║  - maria-claude (features)                     ║
╚═══════════════════════════════════════════════╝
`);

logger.info({
    nodeVersion: process.version,
    platform: process.platform,
    env: process.env.NODE_ENV || "development"
}, "Starting Maria V3");

// Start the server
startServer();
