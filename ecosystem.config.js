module.exports = {
  apps: [
    {
      name: 'smart-exam-backend',
      cwd: '/root/hermes-workspace/smart-exam-checker/backend',
      script: 'venv/bin/python',
      args: '-m uvicorn app.main:app --host 127.0.0.1 --port 8090 --workers 1',
      interpreter: 'none',
      autorestart: true,
      max_memory_restart: '2048M',  # raised for torch AI-detection model (distilgpt2); 800M would restart the process once the model loads
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'smart-exam-frontend',
      cwd: '/root/hermes-workspace/smart-exam-checker/frontend',
      script: 'node_modules/next/dist/bin/next',
      args: 'start',
      interpreter: 'none',
      autorestart: true,
      max_memory_restart: '800M',
      env: {
        NODE_ENV: 'production',
        PORT: '3090',
        HOSTNAME: '127.0.0.1',
      },
    },
  ],
};
