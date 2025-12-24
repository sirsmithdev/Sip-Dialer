import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RootLayout } from '@/components/layout/RootLayout';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { ContactsPage } from '@/pages/ContactsPage';
import { CampaignsPage } from '@/pages/CampaignsPage';
import { ReportsPage } from '@/pages/ReportsPage';

function IvrBuilderPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">IVR Builder</h1>
        <p className="text-muted-foreground">
          Design your interactive voice response flows
        </p>
      </div>
      <div className="rounded-lg border p-6">
        <p className="text-muted-foreground">
          IVR flow builder will be implemented here.
        </p>
      </div>
    </div>
  );
}

function AudioFilesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audio Files</h1>
        <p className="text-muted-foreground">
          Manage your audio prompts and recordings
        </p>
      </div>
      <div className="rounded-lg border p-6">
        <p className="text-muted-foreground">
          Audio file management will be implemented here.
        </p>
      </div>
    </div>
  );
}

export function App() {
  const { fetchUser } = useAuth();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <RootLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="campaigns" element={<CampaignsPage />} />
          <Route path="contacts" element={<ContactsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="ivr" element={<IvrBuilderPage />} />
          <Route path="audio" element={<AudioFilesPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
