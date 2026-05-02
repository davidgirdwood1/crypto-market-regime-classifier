import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BarChart3, Database, ListFilter, RefreshCw } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const regimeOrder = ["Raging Bull", "Bullish", "Sideways", "Bearish", "Raging Bear"];

const regimeClass = {
  "Raging Bear": "raging-bear",
  "Bearish": "bearish",
  "Sideways": "sideways",
  "Bullish": "bullish",
  "Raging Bull": "raging-bull",
};

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function App() {
  const [coins, setCoins] = useState([]);
  const [selected, setSelected] = useState("BTC");
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [showAllRows, setShowAllRows] = useState(false);
  const [tablePage, setTablePage] = useState(1);
  const pageSize = 12;

  useEffect(() => {
    fetchJson("/api/coins")
      .then((data) => {
        setCoins(data);
        if (data[0]?.symbol) {
          setSelected(data[0].symbol);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setError("");
    Promise.all([
      fetchJson(`/api/regime/${selected}/latest`),
      fetchJson(`/api/regime/${selected}/history?limit=1000`),
      fetchJson(`/api/regime/${selected}/explain`),
    ])
      .then(([latestData, historyData, explanationData]) => {
        setLatest(latestData);
        setHistory(historyData);
        setExplanation(explanationData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selected, refreshKey]);

  useEffect(() => {
    setTablePage(1);
  }, [selected, showAllRows]);

  const newestFirstHistory = useMemo(() => history.slice().reverse(), [history]);

  const regimeChangeRows = useMemo(
    () =>
      history
        .filter((row, index) => index === 0 || row.regime !== history[index - 1].regime)
        .reverse(),
    [history],
  );

  const tableRows = showAllRows ? newestFirstHistory : regimeChangeRows;
  const pageCount = Math.max(1, Math.ceil(tableRows.length / pageSize));
  const visibleRows = tableRows.slice((tablePage - 1) * pageSize, tablePage * pageSize);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Portfolio MVP</p>
          <h1>Crypto Market Regime Classifier</h1>
        </div>
        <div className="status-pill">
          <Database size={16} />
          PostgreSQL + FastAPI
        </div>
      </header>

      <section className="control-row">
        <label className="selector">
          <span>Coin</span>
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            {coins.map((coin) => (
              <option key={coin.symbol} value={coin.symbol}>
                {coin.symbol} - {coin.name}
              </option>
            ))}
          </select>
        </label>
        <button className="icon-button" onClick={() => setRefreshKey((value) => value + 1)} title="Refresh data">
          <RefreshCw size={18} />
        </button>
      </section>

      {error && <div className="error-box">{error}</div>}

      <section className="summary-grid">
        <div className={`regime-card ${latest ? regimeClass[latest.regime] : ""}`}>
          <div className="card-label">
            <Activity size={17} />
            Current regime
          </div>
          <h2>{loading ? "Loading" : latest?.regime || "No data"}</h2>
          <p>{latest ? `As of ${latest.date}` : "Run the pipeline to populate predictions."}</p>
        </div>

        <div className="metric-card">
          <div className="card-label">
            <BarChart3 size={17} />
            Confidence
          </div>
          <strong>{latest ? `${Math.round(latest.confidence * 100)}%` : "--"}</strong>
          <p>Classifier probability for the selected regime.</p>
        </div>

        <div className="metric-card">
          <div className="card-label">Latest features</div>
          <dl className="feature-list">
            <div>
              <dt title="Price change over the last 30 days.">30d return</dt>
              <dd>{formatPercent(latest?.features?.return_30d)}</dd>
            </div>
            <div>
              <dt title="Price change over the last 90 days.">90d return</dt>
              <dd>{formatPercent(latest?.features?.return_90d)}</dd>
            </div>
            <div>
              <dt title="How far the current price is below its recent high.">Below recent high</dt>
              <dd>{formatPercent(latest?.features?.drawdown_recent_high)}</dd>
            </div>
            <div>
              <dt title="How far the current price is above or below its 200-day average.">Vs 200d avg</dt>
              <dd>{formatMovingAverageGap(latest?.features?.ma_200_ratio)}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="main-grid">
        <div className="panel chart-panel">
          <h2>Regime Timeline</h2>
          <RegimeTimeline history={history} />
        </div>

        <div className="panel explanation-panel">
          <h2>Explanation</h2>
          <p>{explanation?.explanation || "No explanation available yet."}</p>
          <ul>
            {(explanation?.drivers || []).map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="panel table-panel">
        <div className="table-header">
          <div>
            <h2>{showAllRows ? "Daily Predictions" : "Regime Changes"}</h2>
            <p>
              {showAllRows
                ? "All daily predictions for the selected coin."
                : "Rows appear only when the predicted regime changes."}
            </p>
          </div>
          <button className="mode-button" onClick={() => setShowAllRows((value) => !value)}>
            <ListFilter size={17} />
            {showAllRows ? "Show changes" : "Show all"}
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Est. Price</th>
                <th>Regime</th>
                <th>Confidence</th>
                <th>30d Return</th>
                <th>Volatility</th>
                <th>Below Recent High</th>
                <th>Vs 200d Avg</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={`${row.symbol}-${row.date}`}>
                  <td>{row.date}</td>
                  <td>{formatCurrency(row.price)}</td>
                  <td>
                    <span className={`regime-tag ${regimeClass[row.regime]}`}>{row.regime}</span>
                  </td>
                  <td>{Math.round(row.confidence * 100)}%</td>
                  <td>{formatPercent(row.features.return_30d)}</td>
                  <td>{formatPercent(row.features.rolling_volatility)}</td>
                  <td>{formatPercent(row.features.drawdown_recent_high)}</td>
                  <td>{formatMovingAverageGap(row.features.ma_200_ratio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {showAllRows && (
          <div className="pagination">
            <button
              className="pager-button"
              disabled={tablePage === 1}
              onClick={() => setTablePage((page) => Math.max(1, page - 1))}
            >
              Previous
            </button>
            <span>
              Page {tablePage} of {pageCount}
            </span>
            <button
              className="pager-button"
              disabled={tablePage === pageCount}
              onClick={() => setTablePage((page) => Math.min(pageCount, page + 1))}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </main>
  );
}

function RegimeTimeline({ history }) {
  const timeline = useMemo(() => buildTimeline(history), [history]);

  if (!timeline) {
    return <div className="empty-chart">No regime history available.</div>;
  }

  return (
    <div className="regime-timeline">
      <div className="timeline-plot">
        <div className="timeline-labels">
          {regimeOrder.map((regime) => (
            <div className="timeline-label" key={regime}>
              {regime}
            </div>
          ))}
        </div>
        <div className="timeline-tracks">
          {timeline.ticks.map((tick) => (
            <div className="timeline-gridline" key={tick.date} style={{ left: `${tick.left}%` }}>
              <span>{tick.label}</span>
            </div>
          ))}
          {regimeOrder.map((regime) => (
            <div className="timeline-row" key={regime}>
              {timeline.segments
                .filter((segment) => segment.regime === regime)
                .map((segment) => (
                  <div
                    className={`timeline-segment ${regimeClass[segment.regime]}`}
                    key={`${segment.regime}-${segment.start}-${segment.end}`}
                    style={{ left: `${segment.left}%`, width: `${segment.width}%` }}
                    title={`${segment.regime}: ${segment.start} to ${segment.end} (${segment.confidence}% confidence)`}
                  />
                ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatPercent(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "--";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatMovingAverageGap(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "--";
  const gap = (Number(value) - 1) * 100;
  return `${gap >= 0 ? "+" : ""}${gap.toFixed(1)}%`;
}

function formatCurrency(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "--";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Number(value) >= 100 ? 0 : 4,
  }).format(Number(value));
}

function buildTimeline(history) {
  if (!history.length) return null;

  const datedRows = history.map((row) => ({ ...row, time: toTime(row.date) }));
  const minTime = datedRows[0].time;
  const maxTime = datedRows[datedRows.length - 1].time;
  const totalDays = Math.max(1, daysBetween(minTime, maxTime) + 1);
  const ranges = [];

  let active = {
    regime: datedRows[0].regime,
    start: datedRows[0],
    end: datedRows[0],
    confidences: [datedRows[0].confidence],
  };

  for (const row of datedRows.slice(1)) {
    if (row.regime === active.regime) {
      active.end = row;
      active.confidences.push(row.confidence);
    } else {
      ranges.push(active);
      active = {
        regime: row.regime,
        start: row,
        end: row,
        confidences: [row.confidence],
      };
    }
  }
  ranges.push(active);

  const segments = ranges.map((range) => {
    const left = (daysBetween(minTime, range.start.time) / totalDays) * 100;
    const width = ((daysBetween(range.start.time, range.end.time) + 1) / totalDays) * 100;
    const confidence =
      range.confidences.reduce((sum, value) => sum + Number(value), 0) / range.confidences.length;

    return {
      regime: range.regime,
      start: range.start.date,
      end: range.end.date,
      left,
      width: Math.max(width, 0.8),
      confidence: Math.round(confidence * 100),
    };
  });

  return {
    segments,
    ticks: buildTicks(minTime, maxTime),
  };
}

function buildTicks(minTime, maxTime) {
  const tickCount = 5;
  const span = Math.max(1, maxTime - minTime);

  return Array.from({ length: tickCount }, (_, index) => {
    const time = minTime + (span * index) / (tickCount - 1);
    return {
      date: time,
      left: ((time - minTime) / span) * 100,
      label: new Date(time).toISOString().slice(0, 10),
    };
  });
}

function toTime(date) {
  return new Date(`${date}T00:00:00Z`).getTime();
}

function daysBetween(startTime, endTime) {
  return Math.round((endTime - startTime) / 86400000);
}

createRoot(document.getElementById("root")).render(<App />);
