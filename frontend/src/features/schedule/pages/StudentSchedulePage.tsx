import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { unwrap } from "@/api/errors";
import { texts } from "@/lib/texts";
import { formatTime, formatDayLabel, getLocalDateKey, plural } from "@/lib/datetime";
import { useMe } from "@/features/auth/api";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { PageSkeleton } from "@/components/common/PageSkeleton";
import { PageHeader } from "@/components/common/PageHeader";
import { TelemostButton, BoardButton } from "./LessonButtons";
import { Calendar, Clock, Users } from "lucide-react";

interface Lesson {
  id: number;
  subject: string;
  start_at: string;
  end_at: string;
  status: string;
  video_url_override?: string;
  board_url_override?: string;
  participants_count: number;
}

export function StudentSchedulePage() {
  const { data: me } = useMe();
  const timeZone = me?.timezone || "Europe/Moscow";

  const { data, isPending, isError } = useQuery({
    queryKey: ["student", "lessons"],
    queryFn: async () => {
      const from = new Date();
      from.setDate(from.getDate() - 7);
      const to = new Date();
      to.setDate(to.getDate() + 30);
      const res = await api.GET("/api/v1/student/lessons", {
        params: { query: { from: from.toISOString(), to: to.toISOString() } },
      });
      return unwrap(res);
    },
    enabled: !!me,
  });

  if (isPending) return <PageSkeleton lines={5} />;
  if (isError) return <EmptyState title={texts.schedule.empty} icon={Calendar} />;

  const lessons = (data?.items || []) as Lesson[];
  if (!lessons.length) return <EmptyState title={texts.schedule.empty} icon={Calendar} />;

  // Group by local date
  const grouped = lessons.reduce((acc, lesson) => {
    const key = getLocalDateKey(lesson.start_at, timeZone);
    if (!acc[key]) acc[key] = [];
    acc[key].push(lesson);
    return acc;
  }, {} as Record<string, Lesson[]>);

  const sortedDates = Object.keys(grouped).sort();

  return (
    <div className="container-narrow py-4 safe-top safe-bottom pb-20">
      <PageHeader title="Расписание" subtitle={texts.schedule.today} />

      <div className="space-y-6">
        {sortedDates.map((dateKey) => {
          const dayLessons = grouped[dateKey];
          const firstLesson = dayLessons[0];
          const dateLabel = formatDayLabel(firstLesson.start_at, timeZone);

          return (
            <div key={dateKey} className="space-y-3">
              <h2 className="font-heading font-bold text-sm text-muted-foreground uppercase tracking-wider">
                {dateLabel}
              </h2>
              {dayLessons.map((lesson) => (
                <LessonCard key={lesson.id} lesson={lesson} timeZone={timeZone} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LessonCard({ lesson, timeZone }: { lesson: Lesson; timeZone: string }) {
  const startTime = formatTime(lesson.start_at, timeZone);
  const endTime = formatTime(lesson.end_at, timeZone);
  const relative = formatRelativeTime(lesson.start_at, timeZone);

  return (
    <div className="card-base">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-heading font-bold text-base">{lesson.subject}</span>
            <StatusBadge kind="lesson" status={lesson.status as any} />
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span className="font-heading font-bold text-foreground">{startTime} – {endTime}</span>
            <span className="text-primary font-medium">{relative}</span>
            {lesson.participants_count > 1 && (
              <span className="flex items-center gap-1">
                <Users className="w-3.5 h-3.5" />
                {lesson.participants_count} {plural(lesson.participants_count, texts.plural.student)}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <TelemostButton url={lesson.video_url_override} />
          <BoardButton url={lesson.board_url_override} />
        </div>
      </div>
    </div>
  );
}