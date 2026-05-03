import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import NavBar from '@/components/NavBar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Trading Journal',
  description: 'Local small-cap breakout & gap trade journal',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <NavBar />
        <main className="max-w-screen-2xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  )
}
