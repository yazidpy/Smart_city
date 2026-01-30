"use client"

import React from 'react'
import Link from 'next/link'
import { LayoutDashboard, Video, Camera, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/components/theme-provider'

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <Button onClick={toggleTheme} variant="outline" size="icon" aria-label="Toggle theme">
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/40">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="w-64 shrink-0 border-r bg-card/50 p-4">
          <div className="mb-6">
            <div className="text-sm font-semibold text-foreground">Smart City</div>
            <div className="text-xs text-muted-foreground">Traffic Dashboard</div>
          </div>

          <div className="mb-4 flex items-center justify-between">
            <div className="text-xs text-muted-foreground">Thème</div>
            <ThemeToggle />
          </div>

          <nav className="space-y-1">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted"
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
            <Link
              href="/streaming"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted"
            >
              <Video className="h-4 w-4" />
              Video streaming
            </Link>
            <Link
              href="/cameras"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-muted"
            >
              <Camera className="h-4 w-4" />
              Gestion caméras
            </Link>
          </nav>
        </aside>

        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
