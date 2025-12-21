import axios from 'axios';
import type {
  AuthTokens,
  LoginCredentials,
  User,
  SIPSettings,
  SIPSettingsCreate,
  ConnectionTestResult,
  AudioFile,
  AudioFileListResponse,
  AudioUploadResponse,
  AudioDownloadResponse,
  ContactList,
  ContactListCreate,
  ContactListUpdate,
  ContactListListResponse,
  ContactListContactsResponse,
  FilePreviewResponse,
  ImportConfirmRequest,
  ImportResultResponse,
  DNCEntry,
  DNCEntryCreate,
  DNCListResponse,
  DNCCheckResponse,
  Campaign,
  CampaignListResponse,
  CampaignCreate,
  CampaignUpdate,
  CampaignContactsResponse,
  CampaignStats,
  CampaignScheduleRequest,
  CampaignStatus,
  ContactStatus,
  EmailSettings,
  EmailSettingsCreate,
  EmailSettingsUpdate,
  EmailConnectionTestResult,
  SendTestEmailRequest,
  SendTestEmailResponse,
  EmailLogListResponse,
  SendReportRequest,
  SendReportResponse,
} from '@/types';

const API_BASE_URL = '/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          console.error('Token refresh failed:', refreshError);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login?session=expired';
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthTokens> => {
    const response = await api.post('/auth/login/json', credentials);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};

// SIP Settings API
export const sipSettingsApi = {
  get: async (): Promise<SIPSettings> => {
    const response = await api.get('/settings/sip');
    return response.data;
  },

  create: async (settings: SIPSettingsCreate): Promise<SIPSettings> => {
    const response = await api.post('/settings/sip', settings);
    return response.data;
  },

  update: async (settings: Partial<SIPSettingsCreate>): Promise<SIPSettings> => {
    const response = await api.put('/settings/sip', settings);
    return response.data;
  },

  testConnection: async (): Promise<ConnectionTestResult> => {
    const response = await api.post('/settings/sip/test');
    return response.data;
  },

  delete: async (): Promise<void> => {
    await api.delete('/settings/sip');
  },
};

// Users API
export const usersApi = {
  list: async (): Promise<User[]> => {
    const response = await api.get('/users');
    return response.data;
  },

  get: async (id: string): Promise<User> => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  create: async (user: Partial<User> & { password: string }): Promise<User> => {
    const response = await api.post('/users', user);
    return response.data;
  },

  update: async (id: string, user: Partial<User>): Promise<User> => {
    const response = await api.patch(`/users/${id}`, user);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/users/${id}`);
  },
};

// Audio Files API
export const audioApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    is_active?: boolean;
  }): Promise<AudioFileListResponse> => {
    const response = await api.get('/audio', { params });
    return response.data;
  },

  get: async (id: string): Promise<AudioFile> => {
    const response = await api.get(`/audio/${id}`);
    return response.data;
  },

  upload: async (
    file: File,
    name: string,
    description?: string
  ): Promise<AudioUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    if (description) {
      formData.append('description', description);
    }

    const response = await api.post('/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  update: async (
    id: string,
    data: { name?: string; description?: string; is_active?: boolean }
  ): Promise<AudioFile> => {
    const response = await api.patch(`/audio/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/audio/${id}`);
  },

  getDownloadUrl: async (
    id: string,
    format: string = 'original'
  ): Promise<AudioDownloadResponse> => {
    const response = await api.get(`/audio/${id}/download`, {
      params: { format },
    });
    return response.data;
  },

  getStreamUrl: (id: string, format: string = 'original'): string => {
    const token = localStorage.getItem('access_token');
    return `${API_BASE_URL}/audio/${id}/stream?format=${format}&token=${token}`;
  },
};

// Contacts API
export const contactsApi = {
  // Contact Lists
  listContactLists: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
  }): Promise<ContactListListResponse> => {
    const response = await api.get('/contacts/lists', { params });
    return response.data;
  },

  getContactList: async (id: string): Promise<ContactList> => {
    const response = await api.get(`/contacts/lists/${id}`);
    return response.data;
  },

  createContactList: async (data: ContactListCreate): Promise<ContactList> => {
    const response = await api.post('/contacts/lists', data);
    return response.data;
  },

  updateContactList: async (id: string, data: ContactListUpdate): Promise<ContactList> => {
    const response = await api.patch(`/contacts/lists/${id}`, data);
    return response.data;
  },

  deleteContactList: async (id: string): Promise<void> => {
    await api.delete(`/contacts/lists/${id}`);
  },

  // File Upload
  previewUpload: async (file: File): Promise<FilePreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/contacts/lists/upload/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  confirmUpload: async (data: ImportConfirmRequest): Promise<ImportResultResponse> => {
    const response = await api.post('/contacts/lists/upload/confirm', data);
    return response.data;
  },

  // Contacts within a list
  listContacts: async (
    listId: string,
    params?: {
      page?: number;
      page_size?: number;
      search?: string;
      is_valid?: boolean;
    }
  ): Promise<ContactListContactsResponse> => {
    const response = await api.get(`/contacts/lists/${listId}/contacts`, { params });
    return response.data;
  },

  downloadContacts: async (listId: string): Promise<Blob> => {
    const response = await api.get(`/contacts/lists/${listId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // DNC
  listDNCEntries: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<DNCListResponse> => {
    const response = await api.get('/contacts/dnc', { params });
    return response.data;
  },

  addDNCEntry: async (data: DNCEntryCreate): Promise<DNCEntry> => {
    const response = await api.post('/contacts/dnc', data);
    return response.data;
  },

  checkDNC: async (phoneNumber: string): Promise<DNCCheckResponse> => {
    const response = await api.get('/contacts/dnc/check', {
      params: { phone_number: phoneNumber },
    });
    return response.data;
  },

  removeDNCEntry: async (id: string): Promise<void> => {
    await api.delete(`/contacts/dnc/${id}`);
  },
};

// Campaigns API
export const campaignsApi = {
  // Campaign CRUD
  list: async (params?: {
    page?: number;
    page_size?: number;
    status?: CampaignStatus;
    search?: string;
  }): Promise<CampaignListResponse> => {
    const response = await api.get('/campaigns', { params });
    return response.data;
  },

  get: async (id: string): Promise<Campaign> => {
    const response = await api.get(`/campaigns/${id}`);
    return response.data;
  },

  create: async (data: CampaignCreate): Promise<Campaign> => {
    const response = await api.post('/campaigns', data);
    return response.data;
  },

  update: async (id: string, data: CampaignUpdate): Promise<Campaign> => {
    const response = await api.patch(`/campaigns/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/campaigns/${id}`);
  },

  // Campaign Status Control
  start: async (id: string): Promise<Campaign> => {
    const response = await api.post(`/campaigns/${id}/start`);
    return response.data;
  },

  pause: async (id: string): Promise<Campaign> => {
    const response = await api.post(`/campaigns/${id}/pause`);
    return response.data;
  },

  resume: async (id: string): Promise<Campaign> => {
    const response = await api.post(`/campaigns/${id}/resume`);
    return response.data;
  },

  cancel: async (id: string): Promise<Campaign> => {
    const response = await api.post(`/campaigns/${id}/cancel`);
    return response.data;
  },

  schedule: async (id: string, data: CampaignScheduleRequest): Promise<Campaign> => {
    const response = await api.post(`/campaigns/${id}/schedule`, data);
    return response.data;
  },

  // Campaign Contacts
  listContacts: async (
    campaignId: string,
    params?: {
      page?: number;
      page_size?: number;
      status?: ContactStatus;
    }
  ): Promise<CampaignContactsResponse> => {
    const response = await api.get(`/campaigns/${campaignId}/contacts`, { params });
    return response.data;
  },

  // Campaign Statistics
  getStats: async (id: string): Promise<CampaignStats> => {
    const response = await api.get(`/campaigns/${id}/stats`);
    return response.data;
  },

  // Send Campaign Report
  sendReport: async (id: string, data: SendReportRequest): Promise<SendReportResponse> => {
    const response = await api.post(`/campaigns/${id}/send-report`, data);
    return response.data;
  },
};

// Email Settings API
export const emailSettingsApi = {
  get: async (): Promise<EmailSettings> => {
    const response = await api.get('/settings/email');
    return response.data;
  },

  create: async (settings: EmailSettingsCreate): Promise<EmailSettings> => {
    const response = await api.post('/settings/email', settings);
    return response.data;
  },

  update: async (settings: EmailSettingsUpdate): Promise<EmailSettings> => {
    const response = await api.put('/settings/email', settings);
    return response.data;
  },

  delete: async (): Promise<void> => {
    await api.delete('/settings/email');
  },

  testConnection: async (): Promise<EmailConnectionTestResult> => {
    const response = await api.post('/settings/email/test');
    return response.data;
  },

  sendTestEmail: async (data: SendTestEmailRequest): Promise<SendTestEmailResponse> => {
    const response = await api.post('/settings/email/send-test', data);
    return response.data;
  },

  getLogs: async (params?: {
    email_type?: string;
    status?: string;
    campaign_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<EmailLogListResponse> => {
    const response = await api.get('/settings/email/logs', { params });
    return response.data;
  },
};

export default api;
