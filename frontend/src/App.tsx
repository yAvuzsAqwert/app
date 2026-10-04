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

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/panel" replace />} />
        <Route path="/giris" element={<Login />} />
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
        <Route path="*" element={<Navigate to="/panel" replace />} />
      </Routes>
      <Toaster richColors />
    </>
  );
}
