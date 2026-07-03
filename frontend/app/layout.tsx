import type { Metadata } from 'next'
import { Space_Grotesk, Inter_Tight } from 'next/font/google'
import './globals.css'
import Nav from '@/components/Nav'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

const interTight = Inter_Tight({
  subsets: ['latin'],
  variable: '--font-inter-tight',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'FocusClear — Content Engine',
  description: 'Painel de operação do motor de carrosséis FocusClear',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" className={`${spaceGrotesk.variable} ${interTight.variable}`}>
      <body className="min-h-screen bg-carbon font-body text-neutral-200 antialiased">
        <Nav />
        <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      </body>
    </html>
  )
}
