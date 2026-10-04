import { cn } from "@/lib/utils";

type StatusKind = "lesson" | "assignment" | "attendance" | "bot";
type StatusValue =
  | "scheduled" | "completed" | "cancelled"
  | "assigned" | "submitted" | "needs_revision" | "graded" | "expired" | "is_overdue"
  | "pending" | "attended" | "no_show"
  | "bot_blocked";

interface BadgeConfig {
  label: string;
  variant: "brand" | "success" | "success-tint" | "neutral" | "warning" | "dark" | "danger";
}

const STATUS_MAP: Record<StatusKind, Record<StatusValue, BadgeConfig>> = {
  lesson: {
    scheduled: { label: "Запланирован", variant: "brand" },
    completed: { label: "Проведён", variant: "success" },
    cancelled: { label: "Отменён", variant: "neutral" },
  },
  assignment: {
    assigned: { label: "Выдано", variant: "neutral" },
    submitted: { label: "На проверке", variant: "brand" },
    needs_revision: { label: "На доработку", variant: "warning" },
    graded: { label: "Проверено", variant: "success-tint" },
    expired: { label: "Сгорело", variant: "dark" },
    is_overdue: { label: "Просрочено", variant: "danger" },
  },
  attendance: {
    pending: { label: "Не отмечено", variant: "neutral" },
    attended: { label: "Был", variant: "success-tint" },
    no_show: { label: "Не пришёл", variant: "danger" },
    cancelled: { label: "Отменено", variant: "neutral" },
  },
  bot: {
    bot_blocked: { label: "Бот заблокирован", variant: "danger" },
  },
};

const VARIANT_CLASSES: Record<BadgeConfig["variant"], string> = {
  brand: "bg-green-tint text-green-dark",
  success: "bg-primary text-white",
  "success-tint": "bg-success-bg text-success-fg",
  neutral: "bg-muted text-gray-900 dark:text-gray-200",
  warning: "bg-warning-bg text-warning-fg",
  dark: "bg-gray-900 text-white",
  danger: "bg-danger-bg text-danger-fg",
};

export function StatusBadge({
  kind,
  status,
  className,
}: {
  kind: StatusKind;
  status: StatusValue;
  className?: string;
}) {
  const config = STATUS_MAP[kind]?.[status];
  if (!config) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[8px] text-[11px] font-heading font-extrabold uppercase tracking-wider",
        VARIANT_CLASSES[config.variant],
        className
      )}
    >
      <span className="w-2 h-2 rounded-full bg-current" />
      {config.label}
    </span>
  );
}