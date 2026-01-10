const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const API_KEY = process.env.NEXT_PUBLIC_DASHBOARD_API_KEY || '';

class ApiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;

    if (!this.apiKey) {
      console.warn('NEXT_PUBLIC_DASHBOARD_API_KEY not set. API requests will fail.');
    }
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error ${response.status}: ${errorText || response.statusText}`);
    }

    return response.json();
  }

  getWebSocketUrl(): string {
    // Convert HTTP URL to WebSocket URL and add API key
    const wsBase = this.baseUrl.replace('http://', 'ws://').replace('https://', 'wss://').replace('/api', '');
    return `${wsBase}/api/ws?api_key=${encodeURIComponent(this.apiKey)}`;
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

  async getBars(symbol: string, limit = 390, timeframe = '1Day') {
    return this.request<any[]>(`/bars/${symbol}?limit=${limit}&timeframe=${timeframe}`);
  }

  async getIndicators(symbol: string, timeframe = '5m', limit = 100) {
    return this.request<any[]>(`/indicators/${symbol}?timeframe=${timeframe}&limit=${limit}`);
  }

  async getConfiguration() {
    return this.request<any>('/configuration');
  }
}

export const apiClient = new ApiClient(API_BASE_URL, API_KEY);
