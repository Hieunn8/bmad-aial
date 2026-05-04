import { useEffect, useMemo, useState } from 'react';
import { Area, CartesianGrid, Legend, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ConfidenceBreakdownCard } from '@aial/ui/confidence-breakdown-card';
import { ChartReveal, useChartTheme } from '@aial/ui/chart-reveal';
import { apiRequest } from '../../api/client';

type AlertSummary = {
  alert_id: string;
  metric_name: string;
  domain: string;
  department_scope: string;
  region: string;
  anomaly_timestamp: string;
  deviation_percent: number;
  severity: 'low' | 'medium' | 'high';
  status: 'active' | 'acknowledged' | 'dismissed';
  explanation: string;
  false_positive_rate_30d: number;
  detection_latency_minutes: number;
  created_at: string;
};

type AlertDetail = AlertSummary & {
  isolation_forest_score: number;
  suggested_actions: string[];
  series: Array<{
    timestamp: string;
    actual: number;
    expected_min: number;
    expected_max: number;
    is_anomaly: boolean;
  }>;
  confidence_state: 'low-confidence';
  acknowledged_at?: string | null;
  dismissed_at?: string | null;
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
  padding: '1.35rem 1.35rem 1.2rem',
};

const buttonStyle: React.CSSProperties = {
  border: 'none',
  borderRadius: '999px',
  padding: '0.8rem 1.1rem',
  background: 'linear-gradient(135deg, #0f766e 0%, #115e59 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

const ghostButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: 'rgba(15, 118, 110, 0.09)',
  color: '#115e59',
};

export function AnomalyAlertsPanel(): React.JSX.Element {
  const chartTheme = useChartTheme();
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<AlertDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadAlerts(preferredAlertId?: string | null): Promise<void> {
    const payload = await apiRequest<{ alerts: AlertSummary[] }>('/v1/anomaly-detection/alerts');
    setAlerts(payload.alerts);
    const nextAlertId = preferredAlertId ?? payload.alerts[0]?.alert_id ?? null;
    setSelectedAlertId(nextAlertId);
  }

  async function loadAlertDetail(alertId: string): Promise<void> {
    const detail = await apiRequest<AlertDetail>(`/v1/anomaly-detection/alerts/${alertId}`);
    setSelectedAlert(detail);
  }

  useEffect(() => {
    void (async () => {
      try {
        await loadAlerts();
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Không tải được anomaly alerts');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedAlertId) {
      setSelectedAlert(null);
      return;
    }
    void loadAlertDetail(selectedAlertId).catch((detailError: unknown) => {
      setError(detailError instanceof Error ? detailError.message : 'Không tải được chi tiết anomaly alert');
    });
  }, [selectedAlertId]);

  async function handleRunDetection(): Promise<void> {
    setError(null);
    setStatus(null);
    try {
      const response = await apiRequest<{ latest_alert_id: string; detection_latency_minutes: number; false_positive_rate_30d: number }>(
        '/v1/anomaly-detection/run',
        {
          method: 'POST',
          body: JSON.stringify({
            metric_name: 'order_volume',
            domain: 'sales',
            region: 'HCM',
          }),
        },
      );
      await loadAlerts(response.latest_alert_id);
      setStatus(
        `Đã phát hiện anomaly mới. Alert xuất hiện sau ${response.detection_latency_minutes} phút kể từ lúc dữ liệu sẵn sàng. False positive 30 ngày: ${(response.false_positive_rate_30d * 100).toFixed(1)}%.`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Không thể chạy anomaly detection');
    }
  }

  async function updateAlertState(action: 'acknowledge' | 'dismiss'): Promise<void> {
    if (!selectedAlertId) {
      return;
    }
    setError(null);
    try {
      const response = await apiRequest<{ alert: AlertDetail }>(`/v1/anomaly-detection/alerts/${selectedAlertId}/${action}`, {
        method: 'POST',
      });
      setSelectedAlert(response.alert);
      await loadAlerts(selectedAlertId);
      setStatus(action === 'acknowledge' ? 'Alert đã được xác nhận.' : 'Alert đã được dismiss nhưng vẫn giữ trong history.');
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Không cập nhật được anomaly alert');
    }
  }

  const anomalyPoint = useMemo(
    () => selectedAlert?.series.find((point) => point.is_anomaly) ?? null,
    [selectedAlert],
  );

  return (
    <section id="anomaly-alerts" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Anomaly Alerts</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            Theo dõi bất thường trên time-series đơn hàng, xem giải thích business-readable, và lưu history acknowledge hoặc dismiss.
          </p>
        </div>
        <button type="button" style={buttonStyle} onClick={() => void handleRunDetection()}>
          Run Anomaly Scan
        </button>
      </div>

      {(status || error) && (
        <div
          role={error ? 'alert' : 'status'}
          style={{
            marginTop: '1rem',
            borderRadius: '1rem',
            background: error ? 'rgba(153, 27, 27, 0.08)' : 'rgba(15, 118, 110, 0.08)',
            color: error ? '#991b1b' : '#115e59',
            padding: '0.85rem 0.95rem',
          }}
        >
          {error ?? status}
        </div>
      )}

      <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem', gridTemplateColumns: '0.92fr 1.28fr' }}>
        <aside style={{ display: 'grid', gap: '0.75rem' }}>
          {loading ? (
            <div style={{ color: 'var(--color-neutral-500)' }}>Đang tải anomaly history...</div>
          ) : alerts.length === 0 ? (
            <div style={{ color: 'var(--color-neutral-500)' }}>Chưa có anomaly alert nào trong phạm vi hiện tại.</div>
          ) : (
            alerts.map((alert) => (
              <button
                key={alert.alert_id}
                type="button"
                onClick={() => setSelectedAlertId(alert.alert_id)}
                style={{
                  textAlign: 'left',
                  borderRadius: '1rem',
                  border: selectedAlertId === alert.alert_id ? '1px solid #0f766e' : '1px solid rgba(117, 94, 60, 0.14)',
                  background: selectedAlertId === alert.alert_id ? 'rgba(15, 118, 110, 0.08)' : 'rgba(255,255,255,0.74)',
                  padding: '0.9rem 1rem',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem' }}>
                  <strong>{alert.metric_name}</strong>
                  <span style={{ color: alert.severity === 'high' ? '#b91c1c' : alert.severity === 'medium' ? '#b45309' : '#166534', fontWeight: 700 }}>
                    {alert.severity.toUpperCase()}
                  </span>
                </div>
                <div style={{ marginTop: '0.25rem', color: 'var(--color-neutral-500)', fontSize: '0.86rem' }}>
                  {alert.region} • {alert.status} • {new Date(alert.anomaly_timestamp).toLocaleDateString('vi-VN')}
                </div>
                <div style={{ marginTop: '0.45rem', color: 'var(--color-neutral-700)' }}>{alert.explanation}</div>
              </button>
            ))
          )}
        </aside>

        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', marginBottom: '0.8rem' }}>
              <strong>Anomaly timeline</strong>
              <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
                {selectedAlert ? `False positive ${(selectedAlert.false_positive_rate_30d * 100).toFixed(1)}% • latency ${selectedAlert.detection_latency_minutes}m` : 'Chọn alert để xem chart'}
              </span>
            </div>
            <ChartReveal isStreaming={loading}>
              {!selectedAlert ? (
                <div style={{ color: 'var(--color-neutral-500)' }}>Chi tiết anomaly sẽ hiện khi bạn chọn một alert.</div>
              ) : (
                <div style={{ width: '100%', height: 320 }}>
                  <ResponsiveContainer>
                    <LineChart data={selectedAlert.series}>
                      <CartesianGrid stroke={chartTheme.grid} strokeDasharray="4 4" />
                      <XAxis dataKey="timestamp" stroke={chartTheme.text} />
                      <YAxis stroke={chartTheme.text} />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="expected_max" stroke="none" fill={chartTheme.primary} fillOpacity={0.08} isAnimationActive={false} />
                      <Line type="monotone" dataKey="expected_min" name="Expected min" stroke={chartTheme.colors[1]} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="expected_max" name="Expected max" stroke={chartTheme.colors[1]} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="actual" name="Actual orders" stroke={chartTheme.primary} strokeWidth={2} dot={false} isAnimationActive={false} />
                      {anomalyPoint ? (
                        <ReferenceDot
                          x={anomalyPoint.timestamp}
                          y={anomalyPoint.actual}
                          r={7}
                          fill="#dc2626"
                          stroke="#991b1b"
                          label={{ value: 'Anomaly', position: 'top', fill: '#991b1b' }}
                        />
                      ) : null}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </ChartReveal>
          </div>

          {selectedAlert ? (
            <>
              <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
                <div style={{ fontWeight: 700 }}>Business explanation</div>
                <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>{selectedAlert.explanation}</p>
                <div style={{ marginTop: '0.8rem', display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <button type="button" style={ghostButtonStyle} onClick={() => void updateAlertState('acknowledge')}>
                    Acknowledge
                  </button>
                  <button type="button" style={ghostButtonStyle} onClick={() => void updateAlertState('dismiss')}>
                    Dismiss
                  </button>
                </div>
              </div>

              <ConfidenceBreakdownCard
                type={selectedAlert.confidence_state}
                detail={`Isolation Forest score ${selectedAlert.isolation_forest_score}. False positive rolling 30 ngày ${(selectedAlert.false_positive_rate_30d * 100).toFixed(1)}%. Alert này nên được dùng như tín hiệu điều tra sớm.`}
                onActions={selectedAlert.suggested_actions.map((label) => ({ label, onClick: () => {} }))}
              />
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
