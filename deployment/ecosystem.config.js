// PM2 Ecosystem Configuration for AI Employee
// Start with: pm2 start ecosystem.config.js
// Monitor with: pm2 logs
// Stop with: pm2 stop ecosystem.config.js
// Delete with: pm2 delete ecosystem.config.js

module.exports = {
  apps: [
    {
      // Main Orchestrator Process
      name: 'ai-employee',
      script: 'orchestrator.py',
      interpreter: 'python3',
      
      // Process Management
      instances: 1,
      exec_mode: 'fork',
      
      // Auto-restart Configuration
      autorestart: true,
      max_memory_restart: '500M',
      max_restarts: 10,
      min_uptime: '10s',
      listen_timeout: 5000,
      kill_timeout: 5000,
      
      // Environment Variables
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      
      // Logging
      output: 'logs/pm2/orchestrator.log',
      error: 'logs/pm2/orchestrator-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Monitoring & Alerts
      watch: false,  // Set to true to restart on file changes
      ignore_watch: ['AI_Employee_Vault/Logs', 'node_modules', '.git'],
      
      // Advanced Options
      merge_logs: false,
      cron_restart: '0 0 * * *',  // Restart daily at midnight
      graceful_shutdown: true,
      
      // Cluster Mode (optional - set instances > 1 for clustering)
      // instances: 2,
      // exec_mode: 'cluster',
    },
    
    {
      // Watchdog Monitor Process
      name: 'watchdog',
      script: 'watchdog_monitor.py',
      interpreter: 'python3',
      
      // Process Management
      instances: 1,
      exec_mode: 'fork',
      
      // Auto-restart Configuration
      autorestart: true,
      max_memory_restart: '300M',
      max_restarts: 10,
      min_uptime: '10s',
      
      // Environment Variables
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      
      // Logging
      output: 'logs/pm2/watchdog.log',
      error: 'logs/pm2/watchdog-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Monitoring
      watch: false,
      ignore_watch: ['AI_Employee_Vault/Logs', 'node_modules', '.git'],
      
      // Advanced Options
      merge_logs: false,
      cron_restart: '0 1 * * *',  // Restart daily at 1 AM
      graceful_shutdown: true,
    },
    
    {
      // FastAPI Server (Optional - if running separately from Orchestrator)
      // Uncomment to enable separate FastAPI process
      // name: 'api-server',
      // script: 'server.py',
      // interpreter: 'python3',
      // instances: 1,
      // exec_mode: 'fork',
      // autorestart: true,
      // max_memory_restart: '300M',
      // env: {
      //   NODE_ENV: 'production',
      //   PYTHONUNBUFFERED: '1'
      // },
      // output: 'logs/pm2/api-server.log',
      // error: 'logs/pm2/api-server-error.log',
    },
  ],
  
  // Global Configuration
  deploy: {
    production: {
      user: 'root',
      host: 'your-server.com',
      ref: 'origin/main',
      repo: 'git@github.com:your-repo/fte-employee.git',
      path: '/opt/fte-employee',
      'post-deploy': 'npm install && python3 -m pip install -r requirements.txt && pm2 startOrRestart ecosystem.config.js --env production'
    },
    
    development: {
      user: 'developer',
      host: 'dev-server.local',
      ref: 'origin/develop',
      repo: 'git@github.com:your-repo/fte-employee.git',
      path: '/home/developer/fte-employee',
      'post-deploy': 'npm install && python3 -m pip install -r requirements.txt && pm2 startOrRestart ecosystem.config.js --env development'
    }
  }
};

// ============================================================================
// PM2 USAGE GUIDE
// ============================================================================
// 
// Start all processes:
//   pm2 start ecosystem.config.js
//
// Start specific app:
//   pm2 start ecosystem.config.js --only ai-employee
//
// Stop all:
//   pm2 stop ecosystem.config.js
//
// Restart all:
//   pm2 restart ecosystem.config.js
//
// View logs:
//   pm2 logs                    # All processes
//   pm2 logs ai-employee        # Specific app
//   pm2 logs --err              # Error logs only
//   pm2 logs --lines 100        # Last 100 lines
//
// Monitor:
//   pm2 monit                   # Real-time monitoring
//   pm2 status                  # Process status table
//
// Delete processes:
//   pm2 delete ecosystem.config.js
//   pm2 delete ai-employee      # Delete specific app
//
// Auto-start on system boot:
//   pm2 startup
//   pm2 save
//
// Advanced:
//   pm2 describe ai-employee    # Detailed process info
//   pm2 env ai-employee         # Show environment variables
//   pm2 trigger ai-employee     # Manual trigger
//
// ============================================================================
