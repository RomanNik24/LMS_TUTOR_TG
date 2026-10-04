import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useMe } from "@/features/auth/api";

type Role = "student" | "manager" | "owner";

export function RequireRole({ allowed, children }: { allowed: Role[]; children?: React.ReactNode }) {
  const { data: me, isPending } = useMe();
  const location = useLocation();

  if (isPending) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!me) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!allowed.includes(me.role)) {
    return <Navigate to="/" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}