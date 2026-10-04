import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { unwrap } from "@/api/errors";
import { texts } from "@/lib/texts";
import { formatDate, formatTime, plural } from "@/lib/datetime";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { PageSkeleton } from "@/components/common/PageSkeleton";
import { PageHeader } from "@/components/common/PageHeader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { FileText, Clock, AlertCircle, CheckCircle, XCircle, Loader2, Upload, Eye } from "lucide-react";

type TabValue = "active" | "submitted" | "graded" | "expired";

const TABS: { value: TabValue; label: string; icon: React.ReactNode }[] = [
  { value: "active", label: texts.homework.active, icon: <FileText className="w-4 h-4" /> },
  { value: "submitted", label: texts.homework.submitted, icon: <Clock className="w-4 h-4" /> },
  { value: "graded", label: texts.homework.graded, icon: <CheckCircle className="w-4 h-4" /> },
  { value: "expired", label: texts.homework.expired, icon: <XCircle className="w-4 h-4" /> },
];

interface Assignment {
  id: number;
  homework_id: number;
  status: string;
  title: string;
  subject: string;
  due_at: string;
  is_overdue: boolean;
  score?: number;
  max_score?: number;
  teacher_comment?: string;
}

export function StudentHomeworkPage() {
  const [activeTab, setActiveTab] = useState<TabValue>("active");

  const { data, isPending, isError } = useQuery({
    queryKey: ["student", "homework", activeTab],
    queryFn: async () => {
      const res = await api.GET("/api/v1/student/homework", {
        params: { query: { status: activeTab, limit: 100 } },
      });
      return unwrap(res);
    },
  });

  if (isPending) return <PageSkeleton lines={4} />;
  if (isError) return <EmptyState title={texts.homework.empty} icon={FileText} />;

  const assignments = (data?.items || []) as Assignment[];
  if (!assignments.length) {
    return <EmptyState title={texts.homework.empty} icon={FileText} />;
  }

  return (
    <div className="container-narrow py-4 safe-top safe-bottom pb-20">
      <PageHeader title="Домашние задания" />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value} className="gap-1 py-2">
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value} className="mt-4 space-y-3">
            {assignments.map((a) => (
              <AssignmentCard key={a.id} assignment={a} />
            ))}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

function AssignmentCard({ assignment }: { assignment: Assignment }) {
  const [expanded, setExpanded] = useState(false);
  const isOverdue = assignment.is_overdue;
  const isSubmitted = ["submitted", "graded", "needs_revision"].includes(assignment.status);
  const isGraded = assignment.status === "graded";

  return (
    <div className="card-base overflow-hidden">
      <div className="flex items-start gap-3 p-4" onClick={() => setExpanded(!expanded)}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-heading font-bold text-base truncate">{assignment.title}</h3>
            <StatusBadge kind="assignment" status={assignment.status as any} />
            {isOverdue && !isSubmitted && (
              <StatusBadge kind="assignment" status="is_overdue" />
            )}
          </div>
          <p className="text-sm text-muted-foreground">{assignment.subject}</p>
          <div className="flex items-center gap-3 mt-1 text-sm">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              {texts.homework.deadline.replace("{date}", formatDate(assignment.due_at, "Europe/Moscow")).replace("{time}", formatTime(assignment.due_at, "Europe/Moscow"))}
            </span>
            {isGraded && assignment.score !== undefined && assignment.max_score && (
              <span className="font-mono text-primary">
                {assignment.score} / {assignment.max_score} ({Math.round(assignment.score / assignment.max_score * 100)}%)
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm">Подробнее</span>
          <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border px-4 pb-4 space-y-3 bg-muted/30">
          {isOverdue && !isSubmitted && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-danger-bg text-danger-fg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{texts.homework.overdue}</span>
            </div>
          )}
          {assignment.status === "expired" && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-danger-bg text-danger-fg text-sm">
              <XCircle className="w-4 h-4 flex-shrink-0" />
              <span>{texts.homework.expiredText}</span>
            </div>
          )}
          {assignment.status === "needs_revision" && assignment.teacher_comment && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-warning-bg text-warning-fg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{texts.homework.needsRevision}</p>
                <p className="mt-1">{assignment.teacher_comment}</p>
              </div>
            </div>
          )}
          {isGraded && assignment.teacher_comment && (
            <div className="p-3 rounded-lg bg-success-bg text-success-fg text-sm">
              <p className="font-medium">Комментарий преподавателя:</p>
              <p className="mt-1">{assignment.teacher_comment}</p>
            </div>
          )}
          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" asChild>
              <a href={`/app/homework/${assignment.id}`}>
                <Eye className="w-3.5 h-3.5 mr-1.5" />
                Открыть
              </a>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}