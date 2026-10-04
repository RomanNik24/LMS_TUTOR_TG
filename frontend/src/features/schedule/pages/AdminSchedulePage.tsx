import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Plus, Calendar } from "lucide-react";

export function AdminSchedulePage() {
  const { data: me } = useMe();

  return (
    <div className="container-wide py-4 safe-top safe-bottom">
      <PageHeader
        title="Расписание"
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Создать урок
          </Button>
        }
      />

      <EmptyState
        title={texts.admin.emptySchedule}
        icon={Calendar}
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Создать урок
          </Button>
        }
      />
    </div>
  );
}