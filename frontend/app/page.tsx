'use client'

import { useState } from 'react'
import { GitBranch } from 'lucide-react'
import { AgentActivity } from '@/components/dashboard/agent-activity'
import { AiRepairControl } from '@/components/dashboard/ai-repair-control'
import { DashboardHeader } from '@/components/dashboard/dashboard-header'
import { LiveTelemetryLogs } from '@/components/dashboard/live-telemetry-logs'
import { IncidentsList } from '@/components/dashboard/incidents-list'
import { PlaceholderWidget } from '@/components/dashboard/placeholder-widget'
import { ServiceHealthTable } from '@/components/dashboard/service-health-table'
import { StatCards } from '@/components/dashboard/stat-cards'
import { TelemetryChart } from '@/components/dashboard/telemetry-chart'
import { TopologyGraph } from '@/components/dashboard/topology-graph'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { Navbar } from '@/components/layout/navbar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { type GraphPayload } from '@/lib/api'

/**
 * DashboardPage — the central orchestration layer.
 *
 * Graph state is lifted here so that when TopologyGraph fetches or injects a
 * new graph, all downstream panels (AiRepairControl, ServiceHealthTable,
 * IncidentsList, StatCards) immediately reflect the updated data without
 * each component needing its own redundant fetch.
 */
export default function DashboardPage() {
  const [graph, setGraph] = useState<GraphPayload | null | undefined>(undefined)

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Navbar />
        <main className="flex flex-1 flex-col gap-6 p-4 md:p-6">
          <DashboardHeader />

          {/* Stat Cards — live backend health + graph-derived counts */}
          <StatCards graphProp={graph ?? null} />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="flex flex-col gap-6 lg:col-span-2">
              {/* Topology — fetches & injects graph; bubbles updates via onGraphUpdate */}
              <TopologyGraph onGraphUpdate={setGraph} />

              {/* AI Repair — receives graph from topology so no duplicate fetch */}
              <AiRepairControl graphProp={graph ?? null} />
            </div>
            <div className="lg:col-span-1 relative min-h-[400px] lg:min-h-0">
              <div className="absolute inset-0">
                {/* Live Telemetry Logs — animated mock stream */}
                <LiveTelemetryLogs />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <TelemetryChart />
            </div>
            <div className="lg:col-span-1">
              {/* Incidents derived from live graph nodes */}
              <IncidentsList graphProp={graph ?? null} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              {/* Service health table — live graph node rows */}
              <ServiceHealthTable graphProp={graph ?? null} />
            </div>
            <div className="lg:col-span-1">
              <AgentActivity />
            </div>
          </div>

          <PlaceholderWidget
            icon={GitBranch}
            title="Deployment Timeline"
            description="Correlate releases with incidents and performance regressions."
          />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
