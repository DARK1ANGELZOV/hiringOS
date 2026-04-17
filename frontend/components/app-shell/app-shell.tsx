'use client'

import { useState } from 'react'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { Topbar } from './topbar'
import { AIPanel } from './ai-panel'
import { CommandPalette } from './command-palette'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="flex flex-col">
        <Topbar
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onToggleAIPanel={() => setIsAIPanelOpen(!isAIPanelOpen)}
          isAIPanelOpen={isAIPanelOpen}
        />
        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-auto p-6 grid-bg">
            {children}
          </main>
          <AIPanel
            isOpen={isAIPanelOpen}
            onClose={() => setIsAIPanelOpen(false)}
          />
        </div>
      </SidebarInset>
      <CommandPalette
        open={isCommandPaletteOpen}
        onOpenChange={setIsCommandPaletteOpen}
      />
    </SidebarProvider>
  )
}
