import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, description, icon: Icon, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-4 text-center", className)}>
      {Icon && (
        <Icon className={cn("w-10 h-10 text-primary mb-3 opacity-80", "animate-pulse")} />
      )}
      <h3 className="font-heading font-bold text-lg text-foreground mb-1">{title}</h3>
      {description && <p className="text-muted-foreground text-sm mb-4">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}