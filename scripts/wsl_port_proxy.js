const net = require('net');

const LISTEN_PORT = 1450;
const TARGET_PORT = 1451;
const TARGET_HOST = '127.0.0.1';

const server = net.createServer((clientSocket) => {
  const targetSocket = net.connect(TARGET_PORT, TARGET_HOST, () => {
    clientSocket.pipe(targetSocket);
    targetSocket.pipe(clientSocket);
  });

  clientSocket.on('error', () => targetSocket.destroy());
  targetSocket.on('error', () => clientSocket.destroy());
});

server.on('error', (err) => {
  console.error('[WSL Proxy Error]', err.message);
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
  console.log(`[WSL Port Proxy] Reenviando 0.0.0.0:${LISTEN_PORT} -> ${TARGET_HOST}:${TARGET_PORT}`);
});
