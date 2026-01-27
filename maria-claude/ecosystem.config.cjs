module.exports = {
  apps: [{
    name: 'maria-claude',
    script: 'dist/index.js',
    cwd: '/home/fcamacholombardo/maria-claude',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PORT: 3002,
      CHATWOOT_BASE_URL: 'https://agora.humansoftware.mx',
      CHATWOOT_API_TOKEN: '1r298nK4hAqkwa56dZQpZNGp'
    },
    error_file: '/home/fcamacholombardo/logs/maria-claude-error.log',
    out_file: '/home/fcamacholombardo/logs/maria-claude-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true
  }]
};
