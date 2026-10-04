import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTelegramAuth, useLinkAuth } from "../api";
import { getInitData, isTelegramMiniApp, readyTelegram, expandTelegram } from "@/lib/telegram";
import { texts } from "@/lib/texts";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Loader2, LogIn, MessageSquare } from "lucide-react";

export function LoginPage() {
  const navigate = useNavigate();
  const params = useParams();
  const [searchParams] = useSearchParams();
  const token = params.token || searchParams.get("token");
  const [error, setError] = useState<string | null>(null);

  const telegramAuth = useTelegramAuth();
  const linkAuth = useLinkAuth();

  useEffect(() => {
    readyTelegram();
    expandTelegram();

    // Auto-auth via initData if in Mini App
    if (isTelegramMiniApp() && !token) {
      const initData = getInitData();
      if (initData) {
        telegramAuth.mutate(initData, {
          onSuccess: () => navigate("/", { replace: true }),
          onError: (e) => setError(e.message),
        });
      }
    }
  }, []);

  const handleLinkLogin = async () => {
    if (!token) return;
    setError(null);
    try {
      await linkAuth.mutateAsync(token);
      navigate("/", { replace: true });
    } catch (e: any) {
      setError(e.message || texts.auth.invalidLink);
    }
  };

  const handleTelegramLogin = async () => {
    const initData = getInitData();
    if (initData) {
      telegramAuth.mutate(initData, {
        onSuccess: () => navigate("/", { replace: true }),
        onError: (e) => setError(e.message),
      });
    }
  };

  const isLoading = telegramAuth.isPending || linkAuth.isPending;

  if (token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4 safe-top safe-bottom">
        <div className="w-full max-w-md card-base text-center">
          <h1 className="font-display font-extrabold text-2xl uppercase text-foreground mb-2">
            {texts.auth.loginTitle}
          </h1>
          <p className="text-muted-foreground mb-6">{texts.auth.loginWithLink}</p>
          {error && <p className="text-destructive text-sm mb-4">{error}</p>}
          <Button
            className="w-full"
            onClick={handleLinkLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Вход…
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4 mr-2" />
                {texts.auth.loginButton}
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }

  // No token, no initData - show bot link
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 safe-top safe-bottom">
      <div className="w-full max-w-md card-base text-center">
        <MessageSquare className="w-16 h-16 text-primary mx-auto mb-4" />
        <h1 className="font-display font-extrabold text-2xl uppercase text-foreground mb-2">
          {texts.auth.loginTitle}
        </h1>
        <p className="text-muted-foreground mb-6">
          {texts.auth.openInBot.replace("{botUsername}", import.meta.env.VITE_BOT_USERNAME || "bot")}
        </p>
        <Button className="w-full" variant="outline" onClick={() => window.open(`https://t.me/${import.meta.env.VITE_BOT_USERNAME}`, "_blank")}>
          <MessageSquare className="w-4 h-4 mr-2" />
          Открыть бота
        </Button>
      </div>
    </div>
  );
}