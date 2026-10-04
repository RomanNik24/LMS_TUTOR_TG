import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Video, MousePointer2, ExternalLink } from "lucide-react";

interface TelemostButtonProps {
  url?: string;
  variant?: "secondary" | "highlight";
}

export function TelemostButton({ url, variant = "secondary" }: TelemostButtonProps) {
  if (!url) return null;

  const baseClass = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-heading font-medium transition-colors";
  const variants = {
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    highlight: "bg-highlight text-highlight-foreground hover:bg-amber-dark",
  };

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(baseClass, variants[variant])}
    >
      <Video className="w-3.5 h-3.5" />
      Телемост
      <ExternalLink className="w-3 h-3" />
    </a>
  );
}

interface BoardButtonProps {
  url?: string;
}

export function BoardButton({ url }: BoardButtonProps) {
  if (!url) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground text-xs font-heading font-medium hover:bg-secondary/80 transition-colors"
    >
      <MousePointer2 className="w-3.5 h-3.5" />
      Доска
      <ExternalLink className="w-3 h-3" />
    </a>
  );
}