import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChartReveal, useChartTheme } from '@aial/ui/chart-reveal';
import { ExportJobStatus } from '@aial/ui/export-job-status';
import { apiRequest } from '../../api/client';

type DrilldownRow = {
  label: string;
  forecast_value: number;
  share_percent: number;
};

type ExplainabilityJobHandle = {
  job_id: string;
  status: string;
  queue_name: string;
  task_name: string;
  message?: string;
};

type ExplainabilityJobResult = {
  job_id: string;
  status: string;
  top_factors: Array<{ label: string; contribution_percent: number }>;
  confidence_label: string;
};

type DrilldownExplainabilityResult = {
  dimension: 'department' | 'product' | 'region' | 'channel';
  department_scope: string;
  forecast_metric: string;
  drilldown: DrilldownRow[];
  confidence_label: string;
  explanation_status: 'ready' | 'pending';
  top_factors: Array<{ label: string; contribution_percent: number }>;
  business_labels_mapped?: boolean;
  explainability_job?: ExplainabilityJobHandle;
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
  background: 'linear-gradient(135deg, #7c2d12 0%, #9a3412 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
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

export function DrilldownExplainabilityPanel(): React.JSX.Element {
  const chartTheme = useChartTheme();
  const [dimension, setDimension] = useState<'department' | 'product' | 'region' | 'channel'>('region');
  const [shapAvailable, setShapAvailable] = useState(true);
  const [result, setResult] = useState<DrilldownExplainabilityResult | null>(null);
  const [jobHandle, setJobHandle] = useState<ExplainabilityJobHandle | null>(null);
  const [jobResult, setJobResult] = useState<ExplainabilityJobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobHandle?.job_id) {
      return;
    }
    if (jobHandle.status === 'completed' || jobHandle.status === 'failed') {
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const status = await apiRequest<ExplainabilityJobHandle>(`/v1/analytics/explainability-jobs/${jobHandle.job_id}`);
        if (cancelled) {
          return;
        }
        setJobHandle(status);
        if (status.status === 'completed') {
          const nextResult = await apiRequest<ExplainabilityJobResult>(`/v1/analytics/explainability-jobs/${jobHandle.job_id}/result`);
          if (cancelled) {
            return;
          }
          setJobResult(nextResult);
          return;
        }
        window.setTimeout(() => void poll(), 800);
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError instanceof Error ? pollError.message : 'Không thể kiểm tra explainability job');
        }
      }
    };
    void poll();
    return () => {
      cancelled = true;
    };
  }, [jobHandle?.job_id, jobHandle?.status]);

  useEffect(() => {
    if (!jobHandle?.job_id || jobHandle.status !== 'completed' || jobResult) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const nextResult = await apiRequest<ExplainabilityJobResult>(`/v1/analytics/explainability-jobs/${jobHandle.job_id}/result`);
        if (!cancelled) {
          setJobResult(nextResult);
        }
      } catch (resultError) {
        if (!cancelled) {
          setError(resultError instanceof Error ? resultError.message : 'Không thể tải explainability result');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobHandle?.job_id, jobHandle?.status, jobResult]);

  async function handleRun(): Promise<void> {
    setError(null);
    setJobHandle(null);
    setJobResult(null);
    try {
      const nextResult = await apiRequest<DrilldownExplainabilityResult>('/v1/analytics/drilldown-explainability', {
        method: 'POST',
        body: JSON.stringify({ dimension, shap_available: shapAvailable }),
      });
      setResult(nextResult);
      if (nextResult.explainability_job) {
        setJobHandle(nextResult.explainability_job);
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Không thể chạy drill-down explainability');
    }
  }

  const factors = jobResult?.top_factors ?? result?.top_factors ?? [];
  const confidenceLabel = jobResult?.confidence_label ?? result?.confidence_label ?? 'không rõ xu hướng';

  return (
    <section id="drilldown-explainability" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Drill-down Analytics + Explainability</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            Phân rã forecast theo scope được phép và diễn giải 3 yếu tố đóng góp bằng ngôn ngữ kinh doanh.
          </p>
        </div>
        <button type="button" style={buttonStyle} onClick={() => void handleRun()}>
          Phân tích chi tiết theo khu vực
        </button>
      </div>

      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.85rem', gridTemplateColumns: '1fr 1fr' }}>
        <select value={dimension} onChange={(event) => setDimension(event.target.value as 'department' | 'product' | 'region' | 'channel')} style={inputStyle}>
          <option value="region">Khu vực</option>
          <option value="product">Sản phẩm</option>
          <option value="channel">Kênh bán</option>
          <option value="department">Phòng ban</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: 'var(--color-neutral-700)' }}>
          <input type="checkbox" checked={shapAvailable} onChange={(event) => setShapAvailable(event.target.checked)} />
          SHAP available
        </label>
      </div>

      {error ? (
        <div role="alert" style={{ marginTop: '1rem', color: '#991b1b' }}>
          {error}
        </div>
      ) : null}

      {jobHandle ? (
        <div style={{ marginTop: '1rem' }}>
          <ExportJobStatus
            state={jobHandle.status === 'completed' ? 'ready' : jobHandle.status === 'failed' ? 'failed' : 'queued'}
            title="Explainability async fallback"
            detail={jobHandle.message ?? 'Giải thích chi tiết đang được xử lý'}
          />
        </div>
      ) : null}

      <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1.25fr 0.95fr' }}>
        <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', marginBottom: '0.8rem' }}>
            <strong>Drill-down chart</strong>
            <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
              {result ? `${result.dimension} • scope ${result.department_scope}` : 'Chưa có kết quả'}
            </span>
          </div>
          <ChartReveal isStreaming={Boolean(jobHandle && !jobResult)}>
            {!result ? (
              <div style={{ color: 'var(--color-neutral-500)' }}>Chart sẽ hiện sau khi chạy phân tích chi tiết.</div>
            ) : (
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={result.drilldown}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="4 4" />
                    <XAxis dataKey="label" stroke={chartTheme.text} />
                    <YAxis stroke={chartTheme.text} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="forecast_value" name="Forecast value" fill={chartTheme.primary} />
                    <Bar dataKey="share_percent" name="Share %" fill={chartTheme.colors[1]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartReveal>
        </div>

        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Confidence level</div>
            <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>{confidenceLabel}</p>
          </div>

          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Top 3 yếu tố đóng góp</div>
            {factors.length === 0 ? (
              <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-500)' }}>Giải thích chi tiết đang được xử lý</p>
            ) : (
              <div style={{ marginTop: '0.6rem', display: 'grid', gap: '0.6rem' }}>
                {factors.map((factor, index) => (
                  <div key={factor.label} style={{ borderRadius: '0.9rem', background: 'rgba(124,45,18,0.08)', padding: '0.8rem 0.9rem' }}>
                    {`Yếu tố ${index + 1}: ${factor.label} (đóng góp ${factor.contribution_percent}%)`}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
