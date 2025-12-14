import axios from 'axios';
import type {
  ProtocolState,
  ProtocolSummary,
  WorkflowHistory,
  CreateProtocolRequest,
  ApproveProtocolRequest,
} from '../types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export async function createProtocol(request: CreateProtocolRequest): Promise<ProtocolState> {
  const response = await api.post<ProtocolState>('/protocols', request);
  return response.data;
}

export async function getProtocol(threadId: string): Promise<ProtocolState> {
  const response = await api.get<ProtocolState>(`/protocols/${threadId}`);
  return response.data;
}

export async function listProtocols(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<{
  protocols: ProtocolSummary[];
  total: number;
  page: number;
  page_size: number;
}> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('page_size', pageSize.toString());
  if (status) params.set('status', status);

  const response = await api.get(`/protocols?${params.toString()}`);
  return response.data;
}

export async function approveProtocol(
  threadId: string,
  request: ApproveProtocolRequest
): Promise<ProtocolState> {
  const response = await api.post<ProtocolState>(
    `/protocols/${threadId}/approve`,
    request
  );
  return response.data;
}

export async function getProtocolHistory(threadId: string): Promise<WorkflowHistory> {
  const response = await api.get<WorkflowHistory>(`/protocols/${threadId}/history`);
  return response.data;
}

export async function getProtocolVersions(threadId: string): Promise<{
  thread_id: string;
  versions: Array<{
    version: number;
    agent: string;
    timestamp: string;
    changes_summary?: string;
    content: string;
  }>;
  current_version: number;
}> {
  const response = await api.get(`/protocols/${threadId}/versions`);
  return response.data;
}

export async function deleteProtocol(threadId: string): Promise<void> {
  await api.delete(`/protocols/${threadId}`);
}

export async function healthCheck(): Promise<{
  status: string;
  version: string;
  database: string;
  llm_provider: string;
}> {
  const response = await api.get('/health');
  return response.data;
}

export { api };
