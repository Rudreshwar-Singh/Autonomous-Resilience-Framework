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
import { SectionLoader } from '@/components/dashboard/section-loader'
import {
  AgentActivitySkeleton,
  AiRepairSkeleton,
  ChartSkeleton,
  IncidentsSkeleton,
  ServiceHealthSkeleton,
  StatCardsSkeleton,
  TelemetryLogsSkeleton,
  TopologySkeleton,
} from '@/components/dashboard/card-skeletons'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { Navbar } from '@/components/layout/navbar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

export default function DashboardPage() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Navbar />
        <main className="flex flex-1 flex-col gap-6 p-4 md:p-6">
          <DashboardHeader />

          <SectionLoader delay={500} skeleton={<StatCardsSkeleton />}>
            <StatCards />
          </SectionLoader>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="flex flex-col gap-6 lg:col-span-2">
              <SectionLoader delay={700} skeleton={<TopologySkeleton />}>
                <TopologyGraph />
              </SectionLoader>
              <SectionLoader delay={1100} skeleton={<AiRepairSkeleton />}>
                <AiRepairControl />
              </SectionLoader>
            </div>
            <div className="lg:col-span-1">
              <SectionLoader delay={900} skeleton={<TelemetryLogsSkeleton />}>
                <LiveTelemetryLogs />
              </SectionLoader>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <SectionLoader delay={800} skeleton={<ChartSkeleton />}>
                <TelemetryChart />
              </SectionLoader>
            </div>
            <div className="lg:col-span-1">
              <SectionLoader delay={1000} skeleton={<IncidentsSkeleton />}>
                <IncidentsList />
              </SectionLoader>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <SectionLoader delay={900} skeleton={<ServiceHealthSkeleton />}>
                <ServiceHealthTable />
              </SectionLoader>
            </div>
            <div className="lg:col-span-1">
              <SectionLoader delay={1200} skeleton={<AgentActivitySkeleton />}>
                <AgentActivity />
              </SectionLoader>
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
