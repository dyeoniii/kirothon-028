import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig, type Plugin } from 'vite';

// tailwind.config.js 를 바꿔도 실행 중인 개발 서버가 옛 테마(색상 토큰)를 계속 쓰는 문제를 막기 위해,
// 설정 파일이 바뀌면 개발 서버를 자동으로 다시 시작합니다.
function restartOnTailwindConfig(): Plugin {
  const file = path.resolve(process.cwd(), 'tailwind.config.js');
  return {
    name: 'restart-on-tailwind-config',
    configureServer(server) {
      server.watcher.add(file);
      server.watcher.on('change', (changed) => {
        if (path.resolve(changed) === file) void server.restart();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), restartOnTailwindConfig()],
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
});
