import { cn } from "@/lib/utils";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  const message = error instanceof Error ? error.message : "Что-то пошло не так";

  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-4 text-center", className)}>
      <AlertCircle className="w-10 h-10 text-destructive mb-3" />
      <h3 className="font-heading font-bold text-lg text-foreground mb-1">Ошибка</h3>
      <p className="text-muted-foreground text-sm mb-4 max-w-xs">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Повторить
        </Button>
      )}
    </div>
  );
}