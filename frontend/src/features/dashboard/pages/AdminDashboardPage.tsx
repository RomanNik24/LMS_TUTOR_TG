import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { TrendingUp, Users, Clock, AlertCircle, DollarSign } from "lucide-react";

export function AdminDashboardPage() {
  const { data: me } = useMe();

  // TODO: Fetch real data from /api/v1/admin/dashboard/today
  const mockLessons = [
    { id: 1, time: "10:00", subject: "Информатика", students: ["Анна", "Борис"], status: "scheduled" },
    { id: 2, time: "12:00", subject: "Математика", students: ["Виктор"], status: "scheduled" },
    { id: 3, time: "14:00", subject: "Информатика", students: ["Галина"], status: "completed" },
  ];

  const mockReviewQueue = [
    { id: 1, student: "Анна", title: "ДЗ №5: Циклы", subject: "Информатика" },
    { id: 2, student: "Борис", title: "Пробник ЕГЭ", subject: "Информатика" },
  ];

  return (
    <div className="container-wide py-4 safe-top safe-bottom">
      <div className="flex items-center justify-between mb-6">
        <PageHeader title="Сегодня" subtitle={`${new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}`} />
        {me?.role === "owner" && (
          <Card className="bg-highlight/10 border-highlight/20">
            <CardContent className="flex items-center gap-2 px-4 py-2">
              <DollarSign className="w-5 h-5 text-highlight" />
              <span className="font-display font-extrabold text-highlight">Заработано: 45 000 ₽</span>
              <span className="text-muted-foreground">Ожидается: 12 000 ₽</span>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-bold">Уроки на сегодня</h3>
              <span className="text-sm text-muted-foreground">{mockLessons.length}</span>
            </div>
            <div className="space-y-3">
              {mockLessons.map((lesson) => (
                <div key={lesson.id} className="flex items-center justify-between p-3 rounded-lg bg-muted">
                  <div>
                    <p className="font-heading font-bold">{lesson.time} — {lesson.subject}</p>
                    <p className="text-sm text-muted-foreground">{lesson.students.join(", ")}</p>
                  </div>
                  <StatusBadge kind="lesson" status={lesson.status as any} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-bold">ДЗ на проверку</h3>
              <span className="text-sm text-muted-foreground">{mockReviewQueue.length}</span>
            </div>
            <div className="space-y-3">
              {mockReviewQueue.map((hw) => (
                <div key={hw.id} className="flex items-center justify-between p-3 rounded-lg bg-muted">
                  <div>
                    <p className="font-medium">{hw.title}</p>
                    <p className="text-sm text-muted-foreground">{hw.student} · {hw.subject}</p>
                  </div>
                  <StatusBadge kind="assignment" status="submitted" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h3 className="font-heading font-bold mb-4">Не сдали к уроку</h3>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Все сдали вовремя</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h3 className="font-heading font-bold mb-4">Уроки без отметки</h3>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Все отмечены</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h3 className="font-heading font-bold mb-4">Дедлайны в ближайшие 24ч</h3>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Нет срочных дедлайнов</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}