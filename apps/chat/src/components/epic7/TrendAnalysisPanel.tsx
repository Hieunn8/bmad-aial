import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChartReveal, useChartTheme } from '@aial/ui/chart-reveal';

type TrendResult = {
  metric_name: string;
  comparison_type: 'yoy' | 'mom' | 'qoq';
  provider_used: string;
  department_scope: string;
  dimension: 'department' | 'product' | 'region';
  current_period: string;
  previous_period: string;
  current_value: number;
  previous_value: number;
  absolute_change: number;
  percentage_change: number;
  direction: 'tăng' | 'giảm';
  explanation: string;
  contains_jargon: boolean;
  drilldown: Array<{
    label: string;
    current_value: number;
    previous_value: number;
    absolute_change: number;
    percentage_change: number;
  }>;
  generated_at: string;
  cache_hit: boolean;
  cached_at?: string | null;
  cache_similarity?: number | null;
  uat_gate: {
    required_reviewers: string[];
    minimum_clarity_score: number;
    status: string;
  };
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json() as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(117, 94, 60, 0.18)',
  borderRadius: '1.25rem',
  boxShadow: '0 18px 40px rgba(99, 74, 45, 0.08)',
  backdropFilter: 'blur(10px)',
  padding: '1.35rem 1.35rem 1.2rem',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.8rem 0.95rem',
  borderRadius: '0.9rem',
  border: '1px solid rgba(117, 94, 60, 0.22)',
  background: 'rgba(255,255,255,0.92)',
  color: 'var(--color-neutral-900)',
  fontSize: '0.95rem',
};

const buttonStyle: React.CSSProperties = {
  border: 'none',
  borderRadius: '999px',
  padding: '0.8rem 1.1rem',
  background: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

export function TrendAnalysisPanel(): React.JSX.Element {
  const chartTheme = useChartTheme();
  const [metricName, setMetricName] = useState('doanh thu');
  const [comparisonType, setComparisonType] = useState<'yoy' | 'mom' | 'qoq'>('yoy');
  const [dimension, setDimension] = useState<'department' | 'product' | 'region'>('region');
  const [result, setResult] = useState<TrendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summaryCards = useMemo(() => {
    if (!result) {
      return [];
    }
    return [
      { label: 'Current', value: `${result.current_period}: ${result.current_value.toLocaleString('vi-VN')}` },
      { label: 'Previous', value: `${result.previous_period}: ${result.previous_value.toLocaleString('vi-VN')}` },
      { label: 'Absolute change', value: result.absolute_change.toLocaleString('vi-VN') },
      { label: 'Direction', value: `${result.direction} ${Math.abs(result.percentage_change)}%` },
    ];
  }, [result]);

  async function handleRun(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const nextResult = await apiRequest<TrendResult>('/v1/trend-analysis/run', {
        method: 'POST',
        body: JSON.stringify({
          metric_name: metricName,
          comparison_type: comparisonType,
          dimension,
        }),
      });
      setResult(nextResult);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Không thể chạy trend analysis');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="trend-analysis" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Trend Analysis</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            So sánh YoY, MoM, hoặc QoQ với giải thích plain Vietnamese và drill-down theo scope được phép.
          </p>
        </div>
        <button type="button" style={buttonStyle} onClick={() => void handleRun()}>
          Run Trend
        </button>
      </div>

      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.85rem', gridTemplateColumns: '1.4fr 0.8fr 0.8fr' }}>
        <input value={metricName} onChange={(event) => setMetricName(event.target.value)} style={inputStyle} placeholder="Tên metric" />
        <select value={comparisonType} onChange={(event) => setComparisonType(event.target.value as 'yoy' | 'mom' | 'qoq')} style={inputStyle}>
          <option value="yoy">YoY</option>
          <option value="mom">MoM</option>
          <option value="qoq">QoQ</option>
        </select>
        <select value={dimension} onChange={(event) => setDimension(event.target.value as 'department' | 'product' | 'region')} style={inputStyle}>
          <option value="region">Region</option>
          <option value="product">Product</option>
          <option value="department">Department</option>
        </select>
      </div>

      {error ? (
        <div role="alert" style={{ marginTop: '1rem', color: '#991b1b' }}>
          {error}
        </div>
      ) : null}

      <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1.25fr 0.95fr' }}>
        <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', marginBottom: '0.8rem' }}>
            <strong>Trend drill-down</strong>
            <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
              {result ? `${result.provider_used} • ${result.dimension}` : 'Chưa có kết quả'}
            </span>
          </div>
          <ChartReveal isStreaming={loading}>
            {!result ? (
              <div style={{ color: 'var(--color-neutral-500)' }}>Chart sẽ hiện sau khi chạy phân tích xu hướng.</div>
            ) : (
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={result.drilldown}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="4 4" />
                    <XAxis dataKey="label" stroke={chartTheme.text} />
                    <YAxis stroke={chartTheme.text} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="previous_value" name={result.previous_period} fill={chartTheme.colors[1]} />
                    <Bar dataKey="current_value" name={result.current_period} fill={chartTheme.primary} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartReveal>
        </div>

        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Giải thích</div>
            <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>
              {result?.explanation ?? 'Giải thích plain-language sẽ hiện sau khi chạy trend analysis.'}
            </p>
            {result ? (
              <div style={{ marginTop: '0.65rem', color: 'var(--color-neutral-500)', fontSize: '0.86rem' }}>
                {result.cache_hit ? `Kết quả từ cache${result.cache_similarity ? ` • similarity ${Math.round(result.cache_similarity * 100)}%` : ''}` : 'Kết quả mới từ statsmodels-trend'}
              </div>
            ) : null}
          </div>

          {summaryCards.map((card) => (
            <div key={card.label} style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.74)', border: '1px solid rgba(117, 94, 60, 0.14)', padding: '0.85rem 0.95rem' }}>
              <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.82rem', textTransform: 'uppercase' }}>{card.label}</div>
              <div style={{ marginTop: '0.25rem', fontWeight: 700 }}>{card.value}</div>
            </div>
          ))}

          {result ? (
            <div style={{ borderRadius: '1rem', background: 'rgba(29,78,216,0.08)', color: '#1d4ed8', padding: '0.95rem 1rem' }}>
              Manual UAT gate: cần {result.uat_gate.required_reviewers.join(', ')} chấm clarity tối thiểu {result.uat_gate.minimum_clarity_score}/5.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
