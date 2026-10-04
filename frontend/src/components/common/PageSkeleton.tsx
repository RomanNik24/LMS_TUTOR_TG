import { cn } from "@/lib/utils";

interface PageSkeletonProps {
  className?: string;
  lines?: number;
}

export function PageSkeleton({ className, lines = 3 }: PageSkeletonProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="h-8 w-3/4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-20 w-full bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
      ))}
    </div>
  );
}