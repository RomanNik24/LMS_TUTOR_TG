import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Plus, Users, Search } from "lucide-react";

export function AdminStudentsPage() {
  const { data: me } = useMe();

  return (
    <div className="container-wide py-4 safe-top safe-bottom">
      <PageHeader
        title="Ученики"
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            {texts.admin.student.new}
          </Button>
        }
      />

      <EmptyState
        title={texts.admin.emptyStudents}
        icon={Users}
        action={
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            {texts.admin.student.new}
          </Button>
        }
      />
    </div>
  );
}