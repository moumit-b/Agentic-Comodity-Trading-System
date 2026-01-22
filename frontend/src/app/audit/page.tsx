'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { FileText, Filter, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';

type AuditLog = {
  id: number;
  timestamp: string;
  event_type: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  component: string;
  message: string;
  metadata?: any;
};

export default function AuditPage() {
  const { data: logs } = useApi(async () => {
    try {
      // Fetch decisions from API
      const decisions = await apiClient.getDecisions(100);
      
      // Map to AuditLog format
      return decisions.map((d: any) => ({
        id: d.id,
        timestamp: d.timestamp,
        event_type: d.approved ? 'TRADE_APPROVED' : 'TRADE_REJECTED',
        severity: (d.approved ? 'INFO' : 'WARNING') as AuditLog['severity'],
        component: 'RiskManager',
        message: d.approved 
          ? `Trade approved for execution` 
          : `Trade rejected: ${d.rejection_reason || 'Unknown reason'}`,
        metadata: {
          signal_id: d.signal_id,
          position_size: d.position_size,
          risk_amount: d.risk_amount,
          risk_pct: d.risk_pct
        }
      }));
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      return [];
    }
  }, 10000);

  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [componentFilter, setComponentFilter] = useState<string>('ALL');

  const filtered = logs?.filter((log: AuditLog) => {
    if (severityFilter !== 'ALL' && log.severity !== severityFilter) return false;
    if (componentFilter !== 'ALL' && log.component !== componentFilter) return false;
    return true;
  }) || [];

  const components = [...new Set(logs?.map((l: AuditLog) => l.component) || [])];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <FileText className="w-8 h-8 text-accent-cyan" />
          <h1 className="text-3xl font-medium text-accent-cyan tracking-tight">Audit Log</h1>
        </div>
        <div className="text-sm text-terminal-text-secondary">
          Showing {filtered.length} of {logs?.length || 0} events
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="w-5 h-5 text-accent-purple" />
          <span className="font-medium">Filters</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-terminal-text-secondary mb-2">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent-purple"
            >
              <option value="ALL">All Severities</option>
              <option value="INFO">Info</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-terminal-text-secondary mb-2">Component</label>
            <select
              value={componentFilter}
              onChange={(e) => setComponentFilter(e.target.value)}
              className="w-full bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent-purple"
            >
              <option value="ALL">All Components</option>
              {components.map((component) => (
                <option key={component} value={component}>{component}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Audit Logs */}
      <div className="space-y-2">
        {filtered.map((log: AuditLog) => (
          <div
            key={log.id}
            className={`glass-card p-4 border-l-4 ${getSeverityBorderColor(log.severity)}`}
          >
            <div className="flex items-start space-x-4">
              {/* Severity Icon */}
              <div className="flex-shrink-0 mt-1">
                {getSeverityIcon(log.severity)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${getSeverityClass(log.severity)}`}>
                      {log.severity}
                    </span>
                    <span className="text-xs px-2 py-1 rounded bg-terminal-bg text-terminal-text-secondary">
                      {log.component}
                    </span>
                    <span className="text-xs text-terminal-text-secondary font-mono">
                      {log.event_type}
                    </span>
                  </div>
                  <span className="text-xs text-terminal-text-secondary font-mono">
                    {formatDateTime(log.timestamp)}
                  </span>
                </div>

                <div className="text-sm text-white mb-2">
                  {log.message}
                </div>

                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-accent-cyan cursor-pointer hover:text-accent-purple">
                      View metadata
                    </summary>
                    <pre className="mt-2 p-3 bg-terminal-bg rounded text-xs font-mono text-terminal-text-secondary overflow-x-auto">
                      {JSON.stringify(log.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getSeverityIcon(severity: string) {
  switch (severity) {
    case 'INFO':
      return <Info className="w-5 h-5 text-accent-cyan" />;
    case 'WARNING':
      return <AlertTriangle className="w-5 h-5 text-warning" />;
    case 'ERROR':
      return <XCircle className="w-5 h-5 text-loss" />;
    case 'CRITICAL':
      return <XCircle className="w-5 h-5 text-loss" />;
    default:
      return <CheckCircle className="w-5 h-5 text-profit" />;
  }
}

function getSeverityClass(severity: string) {
  switch (severity) {
    case 'INFO':
      return 'bg-accent-cyan/20 text-accent-cyan';
    case 'WARNING':
      return 'bg-warning/20 text-warning';
    case 'ERROR':
      return 'bg-loss/20 text-loss';
    case 'CRITICAL':
      return 'bg-loss/30 text-loss border border-loss';
    default:
      return 'bg-terminal-border text-terminal-text-secondary';
  }
}

function getSeverityBorderColor(severity: string) {
  switch (severity) {
    case 'INFO':
      return 'border-accent-cyan';
    case 'WARNING':
      return 'border-warning';
    case 'ERROR':
      return 'border-loss';
    case 'CRITICAL':
      return 'border-loss';
    default:
      return 'border-terminal-border';
  }
}

// Mock data generator - replace with actual API call
function generateMockLogs(): AuditLog[] {
  const now = new Date();
  const components = ['CoordinatorAgent', 'RiskManager', 'StrategySelector', 'AlpacaService', 'CircuitBreaker', 'Database'];
  const eventTypes = [
    'SIGNAL_GENERATED',
    'SIGNAL_APPROVED',
    'SIGNAL_REJECTED',
    'TRADE_EXECUTED',
    'POSITION_OPENED',
    'POSITION_CLOSED',
    'CIRCUIT_BREAKER_TRIGGERED',
    'RISK_LIMIT_REACHED',
    'MARKET_DATA_RECEIVED',
    'DATABASE_QUERY',
    'API_REQUEST',
    'SYSTEM_STARTUP',
  ];

  return Array.from({ length: 100 }, (_, i) => {
    const severity: AuditLog['severity'] =
      i % 20 === 0 ? 'CRITICAL' :
      i % 10 === 0 ? 'ERROR' :
      i % 5 === 0 ? 'WARNING' : 'INFO';

    const component = components[i % components.length];
    const eventType = eventTypes[i % eventTypes.length];
    const timestamp = new Date(now.getTime() - i * 60000).toISOString();

    return {
      id: i + 1,
      timestamp,
      event_type: eventType,
      severity,
      component,
      message: generateMessage(eventType, severity),
      metadata: i % 3 === 0 ? {
        execution_id: Math.floor(Math.random() * 1000),
        symbol: ['USO', 'UNG'][i % 2],
        user: 'system',
      } : undefined,
    };
  });
}

function generateMessage(eventType: string, severity: string): string {
  const messages: Record<string, string> = {
    SIGNAL_GENERATED: 'New trading signal generated for USO',
    SIGNAL_APPROVED: 'Signal approved by risk manager',
    SIGNAL_REJECTED: 'Signal rejected - insufficient confidence',
    TRADE_EXECUTED: 'Trade successfully executed on Alpaca',
    POSITION_OPENED: 'New position opened for USO LONG',
    POSITION_CLOSED: 'Position closed with realized P&L',
    CIRCUIT_BREAKER_TRIGGERED: 'Circuit breaker DAILY_LOSS_LIMIT activated',
    RISK_LIMIT_REACHED: 'Portfolio heat exceeded 70% threshold',
    MARKET_DATA_RECEIVED: 'Market data updated from Alpaca',
    DATABASE_QUERY: 'Database query executed successfully',
    API_REQUEST: 'API request to Alpaca completed',
    SYSTEM_STARTUP: 'Trading system initialized successfully',
  };

  if (severity === 'ERROR' || severity === 'CRITICAL') {
    return messages[eventType]?.replace('successfully', 'FAILED') || 'System error occurred';
  }

  return messages[eventType] || 'System event logged';
}
