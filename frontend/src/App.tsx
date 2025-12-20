import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RootLayout } from '@/components/layout/RootLayout';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { ContactsPage } from '@/pages/ContactsPage';
import { CampaignsPage } from '@/pages/CampaignsPage';
import { IvrBuilderPage } from '@/pages/IvrBuilderPage';
import { AudioFilesPage } from '@/pages/AudioFilesPage';

export function App() {
  const { fetchUser } = useAuth();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return (
    <BrowserRouter>
      <WebSocketProvider>
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
            <Route path="ivr" element={<IvrBuilderPage />} />
            <Route path="audio" element={<AudioFilesPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </WebSocketProvider>
    </BrowserRouter>
  );
}
