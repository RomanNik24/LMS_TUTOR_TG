import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";

export function StudentReportsPage() {
  const { data: me } = useMe();

  // TODO: Fetch real data from /api/v1/student/reports
  const mockWeeklyData = [
    { week: "1 нед.", avg: 65 },
    { week: "2 нед.", avg: 72 },
    { week: "3 нед.", avg: 78 },
    { week: "4 нед.", avg: 82 },
  ];

  const mockExamData = [
    { date: "01.10", score: 70, type: "ЕГЭ Инф" },
    { date: "15.10", score: 75, type: "ЕГЭ Инф" },
    { date: "01.11", score: 80, type: "ЕГЭ Инф" },
  ];

  return (
    <div className="container-narrow py-4 safe-top safe-bottom pb-20">
      <PageHeader title="Отчёты" subtitle="Твой прогресс" />

      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-bold">Средний процент ДЗ по неделям</h3>
              <span className="font-display font-extrabold text-2xl text-highlight">
                {mockWeeklyData[mockWeeklyData.length - 1]?.avg || 0}%
              </span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockWeeklyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-200)" />
                  <XAxis dataKey="week" stroke="var(--gray-600)" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="var(--gray-600)" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "12px" }} />
                  <Line
                    type="monotone"
                    dataKey="avg"
                    stroke="var(--brand-green)"
                    strokeWidth={3}
                    dot={{ fill: "var(--brand-green)", strokeWidth: 2 }}
                    activeDot={{ r: 6, fill: "var(--brand-amber)" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-sm text-muted-foreground mt-2">Последний результат: {mockWeeklyData[mockWeeklyData.length - 1]?.avg || 0}%</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h3 className="font-heading font-bold mb-4">Пробные экзамены</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockExamData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-200)" />
                  <XAxis dataKey="date" stroke="var(--gray-600)" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="var(--gray-600)" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "12px" }} />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="var(--brand-green)"
                    strokeWidth={3}
                    dot={{ fill: "var(--brand-green)", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold">Сдано в срок</h3>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary" />
                <span className="font-display font-extrabold text-3xl text-foreground">87%</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">За последние 4 недели</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}