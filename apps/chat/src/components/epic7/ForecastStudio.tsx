import { useEffect, useMemo, useState } from 'react';
import { Area, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChartReveal, useChartTheme } from '@aial/ui/chart-reveal';
import { ConfidenceBreakdownCard } from '@aial/ui/confidence-breakdown-card';
import { ExportJobStatus } from '@aial/ui/export-job-status';
import { apiRequest } from '../../api/client';
import { useAuth } from '../../auth/AuthProvider';

type ForecastJobHandle = {
  job_id: string;
  status: string;
  queue_name: string;
  task_name: string;
  heavy_job: boolean;
  estimated_wait_seconds?: number | null;
  estimated_wait_message?: string | null;
};

type ForecastJobStatus = {
  job_id: string;
  status: string;
  queue_name: string;
  task_name: string;
  heavy_job: boolean;
  estimated_wait_seconds?: number | null;
  estimated_wait_message?: string | null;
  provider_used?: string | null;
  mape?: number | null;
  download_url?: string | null;
  cached_until?: string | null;
  error?: string | null;
};

type ForecastResult = {
  query: string;
  provider_used: string;
  fallback_used: boolean;
  mape: number;
  confidence_state: 'forecast-uncertainty';
  generated_at: string;
  summary: string;
  series: Array<{
    period: string;
    channel: string;
    actual?: number | null;
    forecast?: number | null;
    lower_80?: number | null;
    upper_80?: number | null;
    lower_95?: number | null;
    upper_95?: number | null;
    point_type: 'historical' | 'forecast';
  }>;
};

const FORECAST_JOB_STORAGE_KEY = 'aial-forecast-job';

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
  background: 'linear-gradient(135deg, #9a3412 0%, #c2410c 100%)',
  color: 'white',
  fontWeight: 700,
  cursor: 'pointer',
};

const ghostButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: 'rgba(154, 52, 18, 0.09)',
  color: '#9a3412',
};

function formatForecastFailure(errorCode?: string | null): string {
  if (errorCode === 'queue_timeout') {
    return 'Forecast job đã chờ quá 30 phút trong hàng đợi forecast-batch. Hãy thử lại.';
  }
  if (errorCode === 'cached_result_expired') {
    return 'Kết quả forecast đã hết hạn. Hãy chạy lại để lấy dữ liệu mới.';
  }
  return errorCode ?? 'Forecast job thất bại';
}

export function ForecastStudio(): React.JSX.Element {
  const auth = useAuth();
  const chartTheme = useChartTheme();
  const [query, setQuery] = useState('Dự báo doanh thu Q3 2026 theo kênh phân phối');
  const [job, setJob] = useState<ForecastJobHandle | null>(null);
  const [jobStatus, setJobStatus] = useState<ForecastJobStatus | null>(null);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const persistedJobId = window.sessionStorage.getItem(FORECAST_JOB_STORAGE_KEY);
    if (!persistedJobId) {
      return;
    }
    setJob({
      job_id: persistedJobId,
      status: 'queued',
      queue_name: 'forecast-batch',
      task_name: 'forecast.time_series.generate_report',
      heavy_job: false,
    });
    setStatusMessage('Đã khôi phục forecast job gần nhất để tiếp tục theo dõi kết quả.');
  }, []);

  useEffect(() => {
    if (!job?.job_id) {
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const nextStatus = await apiRequest<ForecastJobStatus>(`/v1/forecast/${job.job_id}`);
        if (cancelled) {
          return;
        }
        setJobStatus(nextStatus);
        if (nextStatus.status === 'completed') {
          const nextResult = await apiRequest<ForecastResult>(`/v1/forecast/${job.job_id}/result`);
          if (cancelled) {
            return;
          }
          setResult(nextResult);
          window.sessionStorage.setItem(FORECAST_JOB_STORAGE_KEY, job.job_id);
          setStatusMessage('Forecast hoàn tất. Có thể xem chart hoặc tải kết quả JSON.');
          return;
        }
        if (nextStatus.status === 'expired') {
          window.sessionStorage.removeItem(FORECAST_JOB_STORAGE_KEY);
          setStatusMessage('Kết quả forecast đã hết hạn sau 60 phút. Hãy chạy lại nếu cần dữ liệu mới.');
          return;
        }
        if (nextStatus.status === 'failed') {
          window.sessionStorage.removeItem(FORECAST_JOB_STORAGE_KEY);
          setError(formatForecastFailure(nextStatus.error));
          return;
        }
        window.setTimeout(() => void poll(), 1200);
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError instanceof Error ? pollError.message : 'Không thể kiểm tra forecast job');
        }
      }
    };
    void poll();
    return () => {
      cancelled = true;
    };
  }, [job]);

  const chartRows = useMemo(() => {
    if (!result) {
      return [];
    }
    const rowMap = new Map<string, Record<string, string | number | null>>();
    for (const point of result.series) {
      const key = `${point.period}`;
      const existing = rowMap.get(key) ?? { period: point.period };
      if (point.point_type === 'historical') {
        existing[`${point.channel}_actual`] = point.actual ?? null;
      } else {
        existing[`${point.channel}_forecast`] = point.forecast ?? null;
        existing[`${point.channel}_lower_95`] = point.lower_95 ?? null;
        existing[`${point.channel}_upper_95`] = point.upper_95 ?? null;
      }
      rowMap.set(key, existing);
    }
    return Array.from(rowMap.values());
  }, [result]);

  async function handleRunForecast(): Promise<void> {
    setError(null);
    setStatusMessage(null);
    setResult(null);
    setJobStatus(null);
    try {
      const nextJob = await apiRequest<ForecastJobHandle>('/v1/forecast/run', {
        method: 'POST',
        body: JSON.stringify({ query }),
      });
      window.sessionStorage.setItem(FORECAST_JOB_STORAGE_KEY, nextJob.job_id);
      setJob(nextJob);
      setStatusMessage(
        nextJob.estimated_wait_message
          ? `Forecast job ${nextJob.job_id} đã vào queue ${nextJob.queue_name}. ${nextJob.estimated_wait_message}`
          : `Forecast job ${nextJob.job_id} đã vào queue ${nextJob.queue_name}.`,
      );
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Không thể chạy forecast');
    }
  }

  async function handleDownload(): Promise<void> {
    if (!job?.job_id) {
      return;
    }
    const response = await fetch(`/v1/forecast/${job.job_id}/download`, {
      headers: auth.session?.accessToken ? { Authorization: `Bearer ${auth.session.accessToken}` } : undefined,
    });
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const filename = disposition.match(/filename="(.+)"/)?.[1] ?? `forecast-${job.job_id}.xlsx`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const jobVisualState =
    jobStatus?.status === 'completed'
      ? 'ready'
      : jobStatus?.status === 'failed'
        ? 'failed'
        : jobStatus?.status === 'expired'
          ? 'expired'
          : jobStatus?.status === 'running'
            ? 'running'
            : jobStatus?.status === 'queued'
              ? 'queued'
              : null;

  return (
    <section id="forecast-studio" style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Forecast Studio</h2>
          <p style={{ margin: '0.35rem 0 0', color: 'var(--color-neutral-600)', lineHeight: 1.6 }}>
            Chạy forecast bất đồng bộ, theo dõi trạng thái job, và xem chart với confidence band.
          </p>
        </div>
        <div style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
          {jobStatus ? `Job: ${jobStatus.status}` : 'No forecast job'}
        </div>
      </div>

      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.85rem', gridTemplateColumns: '1fr auto' }}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={inputStyle}
          placeholder="Nhập yêu cầu forecast"
        />
        <button type="button" style={buttonStyle} onClick={() => void handleRunForecast()}>
          Run Forecast
        </button>
      </div>

      {jobVisualState ? (
        <div style={{ marginTop: '1rem' }}>
          <ExportJobStatus
            state={jobVisualState}
            title={jobStatus?.heavy_job ? 'Forecast batch lớn' : 'Forecast tiêu chuẩn'}
            detail={
              jobStatus?.status === 'completed'
                ? `Kết quả được cache tới ${jobStatus.cached_until ? new Date(jobStatus.cached_until).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '60 phút kể từ lúc hoàn tất'}.`
                : jobStatus?.status === 'failed'
                  ? `Job thất bại: ${formatForecastFailure(jobStatus.error)}`
                  : `Queue ${jobStatus?.queue_name ?? job?.queue_name ?? 'forecast-batch'} • Task ${jobStatus?.task_name ?? job?.task_name ?? 'forecast.time_series.generate_report'}`
            }
            etaLabel={jobStatus?.estimated_wait_message ?? job?.estimated_wait_message ?? null}
          />
        </div>
      ) : null}

      {(statusMessage || error) && (
        <div
          role={error ? 'alert' : 'status'}
          style={{
            marginTop: '1rem',
            borderRadius: '1rem',
            background: error ? 'rgba(153, 27, 27, 0.08)' : 'rgba(154, 52, 18, 0.08)',
            color: error ? '#991b1b' : '#9a3412',
            padding: '0.85rem 0.95rem',
          }}
        >
          {error ?? statusMessage}
        </div>
      )}

      <div style={{ marginTop: '1rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1.3fr 0.9fr' }}>
        <div style={{ borderRadius: '1rem', background: 'rgba(246,241,232,0.82)', padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '0.8rem' }}>
            <strong>Time-series forecast</strong>
            <span style={{ color: 'var(--color-neutral-500)', fontSize: '0.88rem' }}>
              {result ? `${result.provider_used} · MAPE ${(result.mape * 100).toFixed(1)}%` : 'Waiting for result'}
            </span>
          </div>
          <ChartReveal isStreaming={jobStatus?.status === 'queued' || jobStatus?.status === 'running'}>
            {chartRows.length === 0 ? (
              <div style={{ color: 'var(--color-neutral-500)' }}>Chart sẽ hiện khi forecast job hoàn tất.</div>
            ) : (
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={chartRows}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="4 4" />
                    <XAxis dataKey="period" stroke={chartTheme.text} />
                    <YAxis stroke={chartTheme.text} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="Retail_upper_95"
                      stroke="none"
                      fill={chartTheme.primary}
                      fillOpacity={0.08}
                      isAnimationActive={false}
                    />
                    <Line type="monotone" dataKey="Retail_actual" name="Retail historical" stroke={chartTheme.primary} strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="Retail_forecast" name="Retail forecast" stroke={chartTheme.primary} strokeWidth={2} strokeDasharray="7 4" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="Online_actual" name="Online historical" stroke={chartTheme.colors[1]} strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="Online_forecast" name="Online forecast" stroke={chartTheme.colors[1]} strokeWidth={2} strokeDasharray="7 4" dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="Distributor_actual" name="Distributor historical" stroke={chartTheme.colors[2]} strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="Distributor_forecast" name="Distributor forecast" stroke={chartTheme.colors[2]} strokeWidth={2} strokeDasharray="7 4" dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartReveal>
        </div>

        <div style={{ display: 'grid', gap: '0.85rem' }}>
          <div style={{ borderRadius: '1rem', background: 'rgba(255,255,255,0.78)', padding: '1rem', border: '1px solid rgba(117, 94, 60, 0.14)' }}>
            <div style={{ fontWeight: 700 }}>Forecast summary</div>
            <p style={{ margin: '0.45rem 0 0', color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>
              {result?.summary ?? 'Summary sẽ xuất hiện khi forecast hoàn tất.'}
            </p>
            {jobStatus?.status === 'completed' && job?.job_id ? (
              <a
                href={`/v1/forecast/${job.job_id}/download`}
                onClick={(event) => {
                  event.preventDefault();
                  void handleDownload();
                }}
                style={{ display: 'inline-block', textDecoration: 'none', ...ghostButtonStyle, marginTop: '0.8rem' }}
              >
                Download forecast JSON
              </a>
            ) : null}
          </div>

          {result ? (
            <ConfidenceBreakdownCard
              type="forecast-uncertainty"
              detail={`Provider: ${result.provider_used}. MAPE ${(result.mape * 100).toFixed(1)}%. ${result.fallback_used ? 'Đang dùng fallback statsmodels Prophet.' : 'Dùng TimeGPT làm nguồn forecast chính.'}`}
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}
