'use client'

import { Bell, Search } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'

export function Navbar() {
  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-3 backdrop-blur md:px-4">
      <SidebarTrigger className="text-muted-foreground" />
      <Separator orientation="vertical" className="hidden h-6 sm:block" />

      <div className="hidden min-w-0 flex-col leading-tight sm:flex">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-sm font-semibold tracking-tight">AutoHeal</h1>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          AI-Powered Autonomous Resilience Platform
        </p>
      </div>

      <div className="relative ml-auto w-full max-w-xs lg:max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search services, incidents, traces…"
          aria-label="Search"
          className="h-9 pl-9"
        />
      </div>

      <ThemeToggle />

      <Button variant="ghost" size="icon" aria-label="Notifications" className="relative">
        <Bell />
        <span className="absolute right-2 top-2 size-2 rounded-full bg-critical ring-2 ring-background" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button
              type="button"
              aria-label="Open user menu"
              className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Avatar className="size-8">
                <AvatarImage src="/operator-avatar.png" alt="" />
                <AvatarFallback>SR</AvatarFallback>
              </Avatar>
            </button>
          }
        />
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>
            <div className="flex flex-col">
              <span className="text-sm font-medium">Sasha Rivera</span>
              <span className="text-xs text-muted-foreground">sre@autoheal.io</span>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Team &amp; billing</DropdownMenuItem>
            <DropdownMenuItem>API keys</DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
