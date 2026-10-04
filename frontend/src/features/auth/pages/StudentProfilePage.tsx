import { useMe } from "@/features/auth/api";
import { texts } from "@/lib/texts";
import { Button } from "@/components/ui/button";
import { LogOut, User, Settings } from "lucide-react";

export function StudentProfilePage() {
  const { data: me } = useMe();

  return (
    <div className="container-narrow py-6">
      <h1 className="font-display font-extrabold text-2xl uppercase text-foreground mb-6">
        {texts.student.profile}
      </h1>

      <div className="card-base space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="w-8 h-8 text-primary" />
          </div>
          <div>
            <p className="font-heading font-bold text-lg">{me?.display_name || "Ученик"}</p>
            <p className="text-sm text-muted-foreground">ID: {me?.id}</p>
          </div>
        </div>

        <div className="border-t border-border pt-4 space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{texts.student.class}</span>
            <span className="font-medium">—</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{texts.student.timezone}</span>
            <span className="font-medium">{me?.timezone || "Europe/Moscow"}</span>
          </div>
        </div>

        <Button variant="outline" className="w-full mt-4" onClick={() => alert(texts.student.webLoginHint)}>
          <Settings className="w-4 h-4 mr-2" />
          {texts.student.webLogin}
        </Button>

        <Button variant="destructive" className="w-full mt-2">
          <LogOut className="w-4 h-4 mr-2" />
          {texts.student.logout}
        </Button>
      </div>
    </div>
  );
}