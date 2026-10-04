import { Routes, Route, Navigate } from "react-router-dom";
import { RequireRole } from "@/components/common/RequireRole";
import { Layout } from "@/components/common/Layout";

import { LoginPage } from "@/features/auth/pages/LoginPage";
import { StudentSchedulePage } from "@/features/schedule/pages/StudentSchedulePage";
import { StudentHomeworkPage } from "@/features/homework/pages/StudentHomeworkPage";
import { StudentReportsPage } from "@/features/reports/pages/StudentReportsPage";
import { StudentProfilePage } from "@/features/auth/pages/StudentProfilePage";
import { AdminDashboardPage } from "@/features/dashboard/pages/AdminDashboardPage";
import { AdminStudentsPage } from "@/features/students/pages/AdminStudentsPage";
import { AdminSchedulePage } from "@/features/schedule/pages/AdminSchedulePage";
import { AdminHomeworkPage } from "@/features/homework/pages/AdminHomeworkPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/:token" element={<LoginPage />} />

      <Route
        path="/app/*"
        element={
          <RequireRole allowed={["student"]}>
            <Layout role="student" />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="schedule" replace />} />
        <Route path="schedule" element={<StudentSchedulePage />} />
        <Route path="homework" element={<StudentHomeworkPage />} />
        <Route path="reports" element={<StudentReportsPage />} />
        <Route path="profile" element={<StudentProfilePage />} />
      </Route>

      <Route
        path="/admin/*"
        element={
          <RequireRole allowed={["manager", "owner"]}>
            <Layout role="admin" />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="students" element={<AdminStudentsPage />} />
        <Route path="schedule" element={<AdminSchedulePage />} />
        <Route path="homework" element={<AdminHomeworkPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/app/schedule" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;