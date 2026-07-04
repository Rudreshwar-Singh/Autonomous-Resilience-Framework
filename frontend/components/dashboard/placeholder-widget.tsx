import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface PlaceholderWidgetProps {
  title: string
  description: string
  icon: LucideIcon
}

export function PlaceholderWidget({ title, description, icon: Icon }: PlaceholderWidgetProps) {
  return (
    <Card className="group/placeholder h-full border-dashed shadow-sm transition-all duration-200 hover:border-primary/30 hover:shadow-md">
      <CardContent className="flex h-full min-h-40 flex-col items-center justify-center gap-2 text-center">
        <span className="flex size-10 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover/placeholder:bg-primary/10 group-hover/placeholder:text-primary">
          <Icon className="size-5" />
        </span>
        <p className="text-sm font-medium">{title}</p>
        <p className="max-w-[26ch] text-xs text-muted-foreground text-pretty">{description}</p>
      </CardContent>
    </Card>
  )
}
