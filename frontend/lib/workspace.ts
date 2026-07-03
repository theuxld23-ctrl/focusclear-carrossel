// Workspace ativo — guardado no localStorage (v1 = sem auth, escopo por browser).
// Trocar de workspace recarrega a página pra todas as abas refazerem o fetch.

const CHAVE = 'focusclear.workspace'
const PADRAO = 'focusclear'

export function getWorkspace(): string {
  if (typeof window === 'undefined') return PADRAO
  return window.localStorage.getItem(CHAVE) || PADRAO
}

export function setWorkspace(id: string) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(CHAVE, id)
  // Recarrega pra que Nav + todas as páginas montem já com o novo workspace.
  window.location.reload()
}

// Anexa ?workspace_id=<ativo> a um path, preservando querystring existente.
export function comWorkspace(path: string): string {
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}workspace_id=${encodeURIComponent(getWorkspace())}`
}
