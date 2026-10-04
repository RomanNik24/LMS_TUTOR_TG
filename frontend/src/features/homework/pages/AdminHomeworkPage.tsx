import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Plus, FileText } from "lucide-react";

export function AdminHomeworkPage() {
  const { data: me } = useMe();

  return (
    <div className="container-wide py-4 safe-top safe-bottom">
      <PageHeader
        title="Домашние задания"
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            {texts.admin.homework.create}
          </Button>
        }
      />

      <EmptyState
        title={texts.admin.emptyHomework}
        icon={FileText}
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            {texts.admin.homework.create}
          </Button>
        }
      />
    </div>
  );
}