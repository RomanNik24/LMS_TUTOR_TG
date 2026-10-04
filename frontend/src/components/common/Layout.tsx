import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { setupTelegramBackButton, hideTelegramBackButton, readyTelegram, expandTelegram } from "@/lib/telegram";

interface LayoutProps {
  role: "student" | "admin";
  children?: React.ReactNode;
}

export function Layout({ role, children }: LayoutProps) {
  const location = useLocation();

  useEffect(() => {
    readyTelegram();
    expandTelegram();

    const handleBack = () => {
      window.history.back();
    };
    setupTelegramBackButton(handleBack);

    return () => {
      hideTelegramBackButton();
    };
  }, []);

  // Show back button on all non-root routes
  useEffect(() => {
    const isRoot = location.pathname === `/${role === "student" ? "app" : "admin"}`;
    // BackButton visibility handled by setupTelegramBackButton/hideTelegramBackButton
  }, [location.pathname, role]);

  return (
    <div className="min-h-screen bg-background safe-bottom">
      {children ?? <Outlet />}
    </div>
  );
}