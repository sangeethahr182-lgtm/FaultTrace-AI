import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  AlertTriangle, 
  CheckCircle2, 
  Activity, 
  Users, 
  Building2, 
  CloudRain, 
  Wind, 
  Thermometer, 
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  Radio
} from 'lucide-react';
import { fetchOverview, fetchFeeders } from '../api';

export default function OverviewPage({ onNavigateToFaults, onNavigateToRestoration }) {
  const [overview, setOverview] = useState(null);
  const [feeders, setFeeders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [overviewData, feedersData] = await Promise.all([
        fetchOverview(),
        fetchFeeders()
      ]);
      setOverview(overviewData);
      setFeeders(feedersData);
    } catch (err) {
      setError(err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
        <p className="text-gray-400 text-sm">Loading real-time operational overview from backend...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950/40 border border-red-800 rounded-lg p-6 my-6 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-2" />
        <h3 className="text-lg font-semibold text-red-200">Failed to Connect to FaultTrace API</h3>
        <p className="text-sm text-red-300/80 mt-1">{error}</p>
        <button
          onClick={loadData}
          className="mt-4 px-4 py-2 bg-red-800/60 hover:bg-red-700/60 text-white rounded-md text-sm font-medium transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const weather = overview?.weather_summary || {};

  return (
    <div className="space-y-6">
      {/* Active Incident Urgent Banner */}
      {overview?.tripped_feeders > 0 && (
        <div className="bg-red-950/60 border border-red-800/80 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg shadow-red-950/20">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-red-600/20 border border-red-500/40 rounded-lg text-red-400">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs uppercase tracking-wider font-bold bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30">
                  Critical Outage Incident
                </span>
                <span className="text-xs text-gray-400 font-mono">Feeder F4 Tripped</span>
              </div>
              <h2 className="text-base sm:text-lg font-semibold text-white mt-0.5">
                Feeder F4 Lockout • 380 Consumers Outage • 1 Critical Load Impacted (District Water Pump #3)
              </h2>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onNavigateToFaults('F4')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs sm:text-sm font-medium rounded-lg flex items-center space-x-1.5 transition shadow"
            >
              <span>Analyze Fault Root-Cause</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigateToRestoration('F4')}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs sm:text-sm font-medium rounded-lg flex items-center space-x-1.5 transition shadow"
            >
              <span>Advisory Plan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Feeders</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-white">{overview?.total_feeders ?? 0}</div>
            <p className="text-[11px] text-gray-400 mt-0.5">11kV Radial Feeders</p>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Tripped</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <div className="mt-2">
            <div className={`text-2xl font-bold ${(overview?.tripped_feeders ?? 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {overview?.tripped_feeders ?? 0}
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5">Breaker Lockout</p>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Active Faults</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-amber-400">{overview?.active_faults_count ?? 0}</div>
            <p className="text-[11px] text-gray-400 mt-0.5">Under ML Analysis</p>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Affected DTs</span>
            <Building2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-white">{overview?.total_affected_dts ?? 0}</div>
            <p className="text-[11px] text-gray-400 mt-0.5">Distribution Transformers</p>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Affected Consumers</span>
            <Users className="w-4 h-4 text-orange-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-orange-400">{overview?.total_affected_consumers ?? 0}</div>
            <p className="text-[11px] text-gray-400 mt-0.5">Estimated In Outage</p>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-xs">
            <span>Critical Loads</span>
            <ShieldAlert className="w-4 h-4 text-red-500" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-red-400">{overview?.critical_loads_affected ?? 0}</div>
            <p className="text-[11px] text-gray-400 mt-0.5">Hospitals / Water Pumps</p>
          </div>
        </div>
      </div>

      {/* Mid Section: Weather Widget & Feeders Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weather Conditions Card */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <CloudRain className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-semibold text-white">Weather Telemetry</h3>
              </div>
              {weather.is_sample_weather ? (
                <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-600/40 px-2 py-0.5 rounded font-mono">
                  Using Sample Weather
                </span>
              ) : (
                <span className="text-[10px] bg-green-500/20 text-green-300 border border-green-600/40 px-2 py-0.5 rounded font-mono">
                  Open-Meteo Live API
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3 text-center my-4">
              <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
                <Thermometer className="w-4 h-4 text-red-400 mx-auto mb-1" />
                <span className="text-lg font-bold text-white">{weather.temperature_c ?? 22.4}°C</span>
                <p className="text-[10px] text-gray-400">Ambient Temp</p>
              </div>

              <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
                <CloudRain className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                <span className="text-lg font-bold text-blue-400">{weather.rainfall_mm ?? 38.6} mm</span>
                <p className="text-[10px] text-gray-400">Precipitation</p>
              </div>

              <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
                <Wind className="w-4 h-4 text-amber-400 mx-auto mb-1" />
                <span className="text-lg font-bold text-amber-400">{weather.wind_gust_kmh ?? 48.0} km/h</span>
                <p className="text-[10px] text-gray-400">Wind Gust</p>
              </div>
            </div>

            <p className="text-xs text-gray-400 mt-2">
              <span className="text-amber-400 font-medium">Correlation Impact: </span>
              High wind gusts (&gt;45 km/h) combined with heavy rain elevate tree-branch contact probability along 11kV overhead spans.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1F2937] flex items-center justify-between text-xs text-gray-400">
            <span>Synthetic Ref: Bengaluru Hebbal</span>
            <span className="font-mono">13.0358°N, 77.5970°E</span>
          </div>
        </div>

        {/* 11kV Feeders Status Table */}
        <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Radio className="w-5 h-5 text-blue-400" />
              <h3 className="text-sm font-semibold text-white">11kV Feeder Operational Status</h3>
            </div>
            <span className="text-xs text-gray-400">{feeders.length} Feeders Synced</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0A0F1D] text-gray-400 border-b border-[#1F2937]">
                <tr>
                  <th className="py-2.5 px-3">Feeder Code</th>
                  <th className="py-2.5 px-3">Feeder Name</th>
                  <th className="py-2.5 px-3">Rated Cap</th>
                  <th className="py-2.5 px-3">Current Load</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937]">
                {feeders.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-800/30 transition">
                    <td className="py-2.5 px-3 font-mono font-bold text-white">{f.code}</td>
                    <td className="py-2.5 px-3 text-gray-300">{f.name}</td>
                    <td className="py-2.5 px-3 font-mono text-gray-300">{f.rated_capacity_amps} A</td>
                    <td className="py-2.5 px-3 font-mono text-gray-300">{f.current_load_amps} A</td>
                    <td className="py-2.5 px-3">
                      {f.status === 'TRIPPED' ? (
                        <span className="bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded text-[10px] font-bold">
                          TRIPPED
                        </span>
                      ) : (
                        <span className="bg-green-500/20 text-green-400 border border-green-500/30 px-2 py-0.5 rounded text-[10px] font-medium">
                          NORMAL
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-2">
                      <button
                        onClick={() => onNavigateToFaults(f.id)}
                        className="text-xs text-blue-400 hover:text-blue-300 font-medium transition"
                      >
                        Analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent SCADA Events Log */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Recent SCADA & Protection Telemetry Logs</h3>
          </div>
          <span className="text-xs text-gray-400">15-Minute Correlation Window</span>
        </div>

        <div className="space-y-2">
          {overview?.recent_events?.length > 0 ? (
            overview.recent_events.map((evt) => (
              <div
                key={evt.id}
                className="bg-[#0A0F1D] border border-[#1F2937] rounded-lg p-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs"
              >
                <div className="flex items-center space-x-3">
                  <span className="font-mono bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded font-bold">
                    {evt.event_type}
                  </span>
                  <span className="font-mono text-white font-semibold">Feeder {evt.feeder_id}</span>
                  <span className="text-gray-400">• {evt.description}</span>
                </div>
                <div className="flex items-center space-x-4 text-gray-400 font-mono text-[11px]">
                  <span>Surge Current: <strong className="text-white">{evt.current_amps}A</strong></span>
                  <span>Bus Voltage: <strong className="text-white">{evt.voltage_kv}kV</strong></span>
                  <span>{new Date(evt.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500 py-3 text-center">No recent SCADA events logged.</p>
          )}
        </div>
      </div>
    </div>
  );
}
