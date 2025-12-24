import api from './api';
import {
  IVRFlow,
  IVRFlowCreate,
  IVRFlowUpdate,
  IVRFlowListResponse,
  IVRFlowVersionCreate,
  IVRFlowVersion,
} from '@/types/ivr';

export const ivrService = {
  // Flow operations
  async createFlow(data: IVRFlowCreate): Promise<IVRFlow> {
    const response = await api.post('/ivr/flows', data);
    return response.data;
  },

  async listFlows(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<IVRFlowListResponse> {
    const response = await api.get('/ivr/flows', { params });
    return response.data;
  },

  async getFlow(flowId: string, includeVersions = true): Promise<IVRFlow> {
    const response = await api.get(`/ivr/flows/${flowId}`, {
      params: { include_versions: includeVersions },
    });
    return response.data;
  },

  async updateFlow(flowId: string, data: IVRFlowUpdate): Promise<IVRFlow> {
    const response = await api.put(`/ivr/flows/${flowId}`, data);
    return response.data;
  },

  async deleteFlow(flowId: string): Promise<void> {
    await api.delete(`/ivr/flows/${flowId}`);
  },

  // Version operations
  async createVersion(
    flowId: string,
    data: IVRFlowVersionCreate
  ): Promise<IVRFlowVersion> {
    const response = await api.post(`/ivr/flows/${flowId}/versions`, data);
    return response.data;
  },

  async getVersions(flowId: string): Promise<IVRFlowVersion[]> {
    const response = await api.get(`/ivr/flows/${flowId}/versions`);
    return response.data;
  },

  async getVersion(flowId: string, versionId: string): Promise<IVRFlowVersion> {
    const response = await api.get(`/ivr/flows/${flowId}/versions/${versionId}`);
    return response.data;
  },
};
