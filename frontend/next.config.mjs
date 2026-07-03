/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy same-origin /api/* para o backend FastAPI (localhost:8010).
  // Roda server-side no Next — evita CORS e mantém o backend intocado.
  //
  // Rewrites EXPLÍCITOS (não catch-all) para preservar as barras finais que o
  // FastAPI exige nas rotas de coleção (/jobs/, /assets/). O client chama SEM
  // barra final (ex.: /api/jobs) e aqui mapeamos para o path correto do backend
  // — assim o Next não faz o 308 de remoção de barra antes do rewrite.
  async rewrites() {
    const b = process.env.BACKEND_URL || 'http://127.0.0.1:8010'
    return [
      { source: '/api/jobs', destination: `${b}/jobs/` },
      { source: '/api/jobs/:id', destination: `${b}/jobs/:id` },
      { source: '/api/assets', destination: `${b}/assets/` },
      { source: '/api/assets/:id/image', destination: `${b}/assets/:id/image` },
      { source: '/api/assets/:id/status', destination: `${b}/assets/:id/status` },
      { source: '/api/pilares', destination: `${b}/pilares/` },
      { source: '/api/pilares/:id', destination: `${b}/pilares/:id` },
      { source: '/api/tendencias', destination: `${b}/tendencias/` },
      { source: '/api/personagem', destination: `${b}/personagem/` },
      { source: '/api/personagem/foto', destination: `${b}/personagem/foto` },
      { source: '/api/config', destination: `${b}/config/` },
      { source: '/api/health', destination: `${b}/health` },
    ]
  },
}

export default nextConfig
