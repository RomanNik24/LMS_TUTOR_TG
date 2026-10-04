import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { unwrap } from "@/api/errors";
import { texts } from "@/lib/texts";
import { formatDate, formatTime } from "@/lib/datetime";
import { StatusBadge } from "@/components/common/StatusBadge";
import { PageSkeleton } from "@/components/common/PageSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Upload, X, FileText, Check, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Assignment {
  id: number;
  homework_id: number;
  status: string;
  title: string;
  subject: string;
  description?: string;
  due_at: string;
  is_overdue: boolean;
  max_score: number;
  score?: number;
  teacher_comment?: string;
  student_comment?: string;
  materials: { id: number; original_name: string; s3_key: string }[];
  files: { id: number; original_name: string; s3_key: string }[];
}

export function StudentHomeworkDetailPage() {
  const { assignmentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: assignment, isPending, isError } = useQuery({
    queryKey: ["student", "homework", assignmentId],
    queryFn: async () => {
      const res = await api.GET(`/api/v1/student/homework/${assignmentId}`);
      return unwrap(res);
    },
    enabled: !!assignmentId,
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      // Upload files first
      const fileIds: number[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`/api/v1/student/homework/${assignmentId}/files`, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!res.ok) throw new Error("Ошибка загрузки файла");
        const data = await res.json();
        fileIds.push(data.id);
      }

      // Then submit
      const res = await api.POST(`/api/v1/student/homework/${assignmentId}/submit`, {
        body: { student_comment: comment },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student", "homework"] });
      navigate("/app/homework");
    },
    onError: (e: Error) => setError(e.message),
  });

  const selfReportMutation = useMutation({
    mutationFn: async () => {
      const res = await api.POST(`/api/v1/student/homework/${assignmentId}/self-report`, {
        body: { student_comment: comment },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student", "homework"] });
      navigate("/app/homework");
    },
    onError: (e: Error) => setError(e.message),
  });

  if (isPending) return <PageSkeleton lines={6} />;
  if (isError) return <ErrorState error={new Error("Ошибка загрузки")} />;
  if (!assignment) return null;

  const a = assignment as Assignment;
  const isOverdue = a.is_overdue;
  const canSubmit = ["assigned", "needs_revision"].includes(a.status) && !isOverdue && a.status !== "expired";
  const hasFiles = files.length > 0 || a.files.length > 0;

  return (
    <div className="container-narrow py-4 safe-top safe-bottom pb-20">
      <PageHeader title={a.title} />

      <div className="card-base space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-heading font-bold text-base">{a.subject}</span>
          <StatusBadge kind="assignment" status={a.status as any} />
          {isOverdue && <StatusBadge kind="assignment" status="is_overdue" />}
        </div>

        <div className="text-sm text-muted-foreground">
          {texts.homework.deadline.replace("{date}", formatDate(a.due_at, "Europe/Moscow")).replace("{time}", formatTime(a.due_at, "Europe/Moscow"))}
        </div>

        {a.description && <div className="prose prose-sm max-w-none text-foreground">{a.description}</div>}

        {a.materials.length > 0 && (
          <div className="space-y-2">
            <p className="font-medium text-sm">Материалы преподавателя:</p>
            {a.materials.map((m) => (
              <a key={m.id} href={`/api/v1/files/${m.id}/url`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-primary hover:underline">
                <FileText className="w-4 h-4" />
                {m.original_name}
              </a>
            ))}
          </div>
        )}

        <div className="border-t border-border pt-4 space-y-4">
          <h3 className="font-heading font-bold">Твоё решение</h3>

          {a.files.length > 0 && (
            <div className="space-y-2">
              <p className="font-medium text-sm">Загруженные файлы:</p>
              {a.files.map((f) => (
                <div key={f.id} className="flex items-center justify-between p-2 rounded-lg bg-muted">
                  <span className="text-sm truncate flex-1">{f.original_name}</span>
                </div>
              ))}
            </div>
          )}

          <div className={cn("border-2 border-dashed rounded-lg p-4 transition-colors", hasFiles ? "border-primary" : "border-gray-200")}>
            <input
              type="file"
              multiple
              accept="image/*,application/pdf"
              onChange={(e) => {
                const newFiles = Array.from(e.target.files || []);
                if (files.length + newFiles.length > 10) {
                  setError(texts.homework.fileLimit);
                  return;
                }
                for (const f of newFiles) {
                  if (f.size > 10 * 1024 * 1024) {
                    setError(texts.homework.fileSize);
                    return;
                  }
                }
                setFiles((prev) => [...prev, ...newFiles]);
                setError(null);
              }}
              className="hidden"
              id="file-upload"
              ref={(el) => el?.click()}
            />
            <label htmlFor="file-upload" className="flex flex-col items-center gap-3 cursor-pointer">
              <Upload className="w-10 h-10 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {hasFiles ? `${files.length + a.files.length} из 10 файлов` : texts.homework.addFiles}
              </span>
              <span className="text-xs text-muted-foreground">{texts.homework.maxSize}</span>
            </label>
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm bg-muted px-2 py-1 rounded">
                <span className="truncate flex-1">{f.name}</span>
                <span className="text-muted-foreground">{(f.size / 1024).toFixed(1)} KB</span>
                <button onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))} className="text-muted-foreground hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <Label htmlFor="comment" className="text-sm font-medium">
            Комментарий (необязательно)
          </Label>
          <Textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий к решению…"
            rows={3}
          />

          {error && <p className="text-destructive text-sm">{error}</p>}

          {canSubmit && (
            <div className="flex gap-2 pt-2">
              <Button
                className="flex-1"
                onClick={() => submitMutation.mutate()}
                disabled={submitMutation.isPending || !hasFiles}
              >
                {submitMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Отправка…
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    {texts.homework.submit}
                  </>
                )}
              </Button>
              <Button variant="secondary" onClick={() => selfReportMutation.mutate()} disabled={selfReportMutation.isPending}>
                <FileText className="w-4 h-4 mr-2" />
                {texts.homework.selfReport}
              </Button>
            </div>
          )}

          {!canSubmit && a.status !== "graded" && (
            <p className="text-muted-foreground text-sm text-center py-2">
              {a.status === "expired" ? texts.homework.expiredText : "Сдача недоступна"}
            </p>
          )}

          {a.status === "graded" && a.score !== undefined && (
            <div className="text-center py-2">
              <span className="font-display font-extrabold text-3xl text-primary">
                {a.score} / {a.max_score}
              </span>
              <p className="text-muted-foreground text-sm mt-1">
                {Math.round(a.score / a.max_score * 100)}%
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}