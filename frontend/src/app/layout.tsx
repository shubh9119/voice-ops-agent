import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Omnibound — Brand Q&A Agent',
  description: 'RAG-powered brand research and Q&A platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        {children}
      </body>
    </html>
  )
}
