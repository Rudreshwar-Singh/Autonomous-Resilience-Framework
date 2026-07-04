'use client'

import {
  Bot,
  LayoutDashboard,
  LifeBuoy,
  Network,
  ScrollText,
  Server,
  Settings,
} from 'lucide-react'
import { useState } from 'react'
import { Logo } from '@/components/layout/logo'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

const navItems = [
  { title: 'Dashboard', icon: LayoutDashboard, badge: null },
  { title: 'Services', icon: Server, badge: '248' },
  { title: 'Topology', icon: Network, badge: null },
  { title: 'Telemetry', icon: ScrollText, badge: null },
  { title: 'AI Agent', icon: Bot, badge: 'AI' },
  { title: 'Incidents', icon: LifeBuoy, badge: '2' },
  { title: 'Settings', icon: Settings, badge: null },
]

export function AppSidebar() {
  const [active, setActive] = useState('Dashboard')

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-1 py-1.5 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <Logo />
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold tracking-tight">AutoHeal</span>
            <span className="text-xs text-muted-foreground">Resilience Platform</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    isActive={active === item.title}
                    tooltip={item.title}
                    onClick={() => setActive(item.title)}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                  {item.badge ? <SidebarMenuBadge>{item.badge}</SidebarMenuBadge> : null}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="rounded-lg border border-sidebar-border bg-sidebar-accent/50 p-3 group-data-[collapsible=icon]:hidden">
          <p className="text-xs font-medium text-sidebar-accent-foreground">Autopilot enabled</p>
          <p className="mt-1 text-xs text-muted-foreground text-pretty">
            AI agent is actively remediating incidents across your fleet.
          </p>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
