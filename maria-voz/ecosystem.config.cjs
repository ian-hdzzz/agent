module.exports = {
  apps: [{
    name: 'maria-voz',
    script: 'dist/server.js',
    cwd: '/home/fcamacholombardo/maria-voz',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PORT: 3003,
      // Database (same as other maria services)
      PGHOST: 'localhost',
      PGPORT: 5432,
      PGUSER: 'postgres',
      PGPASSWORD: 'e4b03808d2e430d22a3e19f6b0e5adbd',
      PGDATABASE: 'agora_production',
      PGPOOL_MAX: 10,
      // CEA API (uses squid proxy on GCP)
      CEA_PROXY_URL: 'http://localhost:3128',
      // ElevenLabs
      ELEVENLABS_AGENT_ID: 'agent_7301kg0z72effkvtqghs2hx58bpt',
      ELEVENLABS_WEBHOOK_SECRET: '', // Optional: set for security
      // Phone
      WHATSAPP_NUMBER: '442-238-8200'
    },
    error_file: '/home/fcamacholombardo/logs/maria-voz-error.log',
    out_file: '/home/fcamacholombardo/logs/maria-voz-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }]
};
