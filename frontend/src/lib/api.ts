const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async getAccount() {
    return this.request<any>('/account');
  }

  async getPositions() {
    return this.request<any[]>('/positions');
  }

  async getSignals(params?: { limit?: number; strategy?: string; direction?: string }) {
    const query = new URLSearchParams(params as any).toString();
    return this.request<any[]>(`/signals${query ? `?${query}` : ''}`);
  }

  async getExecutions(limit = 50) {
    return this.request<any[]>(`/executions?limit=${limit}`);
  }

  async getPendingConfirmations() {
    return this.request<any[]>('/executions/pending');
  }

  async confirmExecution(id: number, action: 'approve' | 'reject', reason?: string) {
    return this.request(`/executions/${id}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
    });
  }

  async getCircuitBreakers() {
    return this.request<any[]>('/circuit-breakers');
  }

  async managekillSwitch(action: 'activate' | 'clear', reason?: string) {
    return this.request('/kill-switch', {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
    });
  }

  async getRiskMetrics() {
    return this.request<any>('/risk/metrics');
  }

  async getBars(symbol: string, limit = 390) {
    return this.request<any[]>(`/bars/${symbol}?limit=${limit}`);
  }

  async getIndicators(symbol: string, timeframe = '5m', limit = 100) {
    return this.request<any[]>(`/indicators/${symbol}?timeframe=${timeframe}&limit=${limit}`);
  }

  async getConfiguration() {
    return this.request<any>('/configuration');
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
