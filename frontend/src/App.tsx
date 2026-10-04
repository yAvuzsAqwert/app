import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Protected from "@/components/Protected";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import Dealers from "@/pages/Dealers";
import Settings from "@/pages/Settings";
import DailyReport from "@/pages/DailyReport";
import MonthlyReport from "@/pages/MonthlyReport";
import Users from "@/pages/Users";
import AuditLog from "@/pages/AuditLog";
import Portal from "@/pages/Portal";
import PortalLogin from "@/pages/PortalLogin";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/panel" replace />} />
        <Route path="/giris" element={<Login />} />
        {/* Bayi portalı — ekip oturumundan ayrı, salt okunur */}
        <Route path="/bayi-giris" element={<PortalLogin />} />
        <Route path="/bayi" element={<Portal />} />
        <Route
          path="/panel"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route
          path="/projeler"
          element={
            <Protected>
              <Projects />
            </Protected>
          }
        />
        <Route
          path="/projeler/:id"
          element={
            <Protected>
              <ProjectDetail />
            </Protected>
          }
        />
        <Route
          path="/bayiler"
          element={
            <Protected>
              <Dealers />
            </Protected>
          }
        />
        <Route
          path="/tanimlar"
          element={
            <Protected>
              <Settings />
            </Protected>
          }
        />
        <Route
          path="/rapor"
          element={
            <Protected>
              <DailyReport />
            </Protected>
          }
        />
        <Route
          path="/aylik-rapor"
          element={
            <Protected>
              <MonthlyReport />
            </Protected>
          }
        />
        <Route
          path="/islem-gunlugu"
          element={
            <Protected>
              <AuditLog />
            </Protected>
          }
        />
        <Route
          path="/kullanicilar"
          element={
            <Protected>
              <Users />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/panel" replace />} />
      </Routes>
      <Toaster richColors />
    </>
  );
}
