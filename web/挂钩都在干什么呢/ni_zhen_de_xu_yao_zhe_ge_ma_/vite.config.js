import { defineConfig } from 'vite'
import path from 'node:path'

const root = process.cwd()

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,

    allowedHosts: true,

    fs: {
      strict: true,
      allow: [
        root,
        path.join(root, 'src'),
        path.join(root, 'public')
      ],
      deny: ['.env', '.env.*', '*.{crt,pem}', '**/.git/**']
    }
  }
})
