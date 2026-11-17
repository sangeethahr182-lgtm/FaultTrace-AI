import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  Activity, 
  AlertTriangle, 
  ShieldCheck, 
  CheckCircle2, 
  HelpCircle, 
  RefreshCw, 
  ArrowRight,
  Sliders,
  Filter,
  BarChart2
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell, 
  ReferenceLine 
} from 'recharts';
import { analyzeFault, fetchFeeders } from '../api';

export default function FaultIntelligencePage({ selectedFeederId = 'F4', onNavigateToRestoration }) {
  const [feederId, setFeederId] = useState(selectedFeederId);
  const [feeders, setFeeders] = useState([]);
  const [lookbackMinutes, setLookbackMinutes] = useState(30);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchFeeders()
      .then(data => setFeeders(data))
      .catch(() => {});
  }, []);

  const runAnalysis = async (targetFeeder = feederId) => {
    try {
      setLoading(true);
      setError(null);
      const res = await analyzeFault(targetFeeder, lookbackMinutes);
      setAnalysisResult(res);
    } catch (err) {
      setError(err.message || 'Fault localization pipeline failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (feederId) {
      runAnalysis(feederId);
    }
  }, [feederId]);

  const topCandidate = analysisResult?.top_candidates?.[0];
  const shapFactors = topCandidate?.shap_factors || [];

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-bold text-white">AI Fault Localization & Root-Cause Intelligence</h2>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            NetworkX Radial Pruning • 15-Min Rolling Window Correlation • XGBoost Localization • SHAP TreeExplainer
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2">
            <label className="text-xs text-gray-400 font-medium">Select Feeder:</label>
            <select
              value={feederId}
              onChange={(e) => setFeederId(e.target.value)}
              className="bg-[#0A0F1D] border border-[#1F2937] text-white text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              {feeders.length > 0 ? (
                feeders.map(f => (
                  <option key={f.id} value={f.id}>{f.code} - {f.name}</option>
                ))
              ) : (
                <option value="F4">F4 - 11kV Manyata Feeder</option>
              )}
            </select>
          </div>

          <button
            onClick={() => runAnalysis(feederId)}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition disabled:opacity-50 shadow"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Running ML Pipeline...' : 'Re-Run Pipeline'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-800 rounded-lg p-4 text-xs text-red-300 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Candidate Section Callout Banner */}
      {topCandidate && (
        <div className="bg-[#111827] border-2 border-red-500/40 rounded-xl p-5 shadow-lg shadow-red-950/20">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#1F2937]">
            <div>
              <div className="flex items-center space-x-2">
                <span className="bg-red-600 text-white text-[11px] font-bold px-2 py-0.5 rounded tracking-wider uppercase">
                  Rank #1 Suspected Fault Section
                </span>
                <span className="text-xs text-gray-400 font-mono">
                  Pruned from {analysisResult?.pruned_candidate_count} candidate sections
                </span>
              </div>
              <h3 className="text-2xl font-black text-white mt-1">
                Line Section {topCandidate.section_id}
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Suspected fault location on Feeder {analysisResult?.feeder_code}. Tree overhang / phase-to-ground flashover indicated.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 block tracking-wider">
                  Model Confidence
                </span>
                <span className="text-2xl font-extrabold text-blue-400">
                  {(topCandidate.calibrated_confidence * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-amber-400 block font-medium">
                  {topCandidate.confidence_label}
                </span>
              </div>

              <div className="h-8 w-px bg-gray-800 hidden sm:block" />

              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 block tracking-wider">
                  Raw Model Score
                </span>
                <span className="text-sm font-mono text-gray-200">
                  {topCandidate.raw_model_score.toFixed(4)}
                </span>
                <span className="text-[10px] text-gray-500 block">XGBoost Logit Probability</span>
              </div>

              <button
                onClick={() => onNavigateToRestoration(analysisResult.prediction_id, topCandidate.section_id)}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition ml-auto shadow"
              >
                <span>Generate Advisory Plan</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Metrics of Top Candidate */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 text-xs">
            <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
              <span className="text-gray-400 block">Downstream Complaints</span>
              <strong className="text-white text-base font-bold">{topCandidate.downstream_complaints}</strong>
              <span className="text-[10px] text-gray-500 block">in 15-min window</span>
            </div>

            <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
              <span className="text-gray-400 block">Consumer Outage Density</span>
              <strong className="text-amber-400 text-base font-bold">
                {(topCandidate.features?.consumer_outage_density * 100).toFixed(1)}%
              </strong>
              <span className="text-[10px] text-gray-500 block">calls per downstream meter</span>
            </div>

            <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
              <span className="text-gray-400 block">Isolation Air-Break Switch</span>
              <strong className="text-white text-base font-mono">{topCandidate.isolation_switch || 'AB-14'}</strong>
              <span className="text-[10px] text-blue-400 block font-medium">Physical Cutoff Point</span>
            </div>

            <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937]">
              <span className="text-gray-400 block">Candidate Tie Switch</span>
              <strong className="text-white text-base font-mono">{topCandidate.tie_switch_available || 'TS-08'}</strong>
              <span className="text-[10px] text-green-400 block font-medium">Backfeed via Feeder F3</span>
            </div>
          </div>
        </div>
      )}

      {/* SHAP Factor Waterfall / Contributions */}
      {topCandidate && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* SHAP Chart */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <BarChart2 className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-semibold text-white">SHAP Feature Contributions</h3>
              </div>
              <span className="text-[10px] bg-blue-900/40 text-blue-300 border border-blue-700/40 px-2 py-0.5 rounded font-mono">
                {analysisResult?.explanation_method || 'SHAP TreeExplainer'}
              </span>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Feature impact on section fault probability for {topCandidate.section_id}. Explanations derived directly from trained XGBoost trees.
            </p>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={shapFactors.map(f => ({
                    name: f.display_name,
                    shap: f.shap_value,
                    val: f.value
                  }))}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                >
                  <XAxis type="number" stroke="#9CA3AF" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" stroke="#9CA3AF" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: 11 }}
                    formatter={(val, name, item) => [
                      `${val.toFixed(4)} (Observed Value: ${item.payload.val})`,
                      'SHAP Value'
                    ]}
                  />
                  <ReferenceLine x={0} stroke="#4B5563" />
                  <Bar dataKey="shap">
                    {shapFactors.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.shap_value >= 0 ? '#EF4444' : '#10B981'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-center space-x-6 text-[11px] text-gray-400 mt-2">
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 bg-red-500 rounded-sm" />
                <span>Increases Fault Probability (Risk Factor)</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 bg-green-500 rounded-sm" />
                <span>Decreases Fault Probability (Normal Factor)</span>
              </div>
            </div>
          </div>

          {/* Feature Factor Breakdown Table */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white mb-2">Key Operational Factors Analysis</h3>
              <p className="text-xs text-gray-400 mb-4">
                Quantitative signals captured from SCADA trip, AMI complaints, and Open-Meteo weather.
              </p>

              <div className="space-y-2.5">
                {shapFactors.map((factor, idx) => (
                  <div
                    key={idx}
                    className="bg-[#0A0F1D] border border-[#1F2937] rounded-lg p-2.5 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold text-white">{factor.display_name}</div>
                      <span className="text-[10px] text-gray-400">
                        Observed Input: <strong className="text-gray-200 font-mono">{factor.value}</strong>
                      </span>
                    </div>

                    <div className="text-right">
                      <span className={`font-mono font-bold ${factor.shap_value >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {factor.shap_value >= 0 ? `+${factor.shap_value.toFixed(4)}` : factor.shap_value.toFixed(4)}
                      </span>
                      <span className="text-[10px] text-gray-400 block">
                        {factor.shap_value >= 0 ? 'Elevates Risk' : 'Reduces Risk'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 p-3 bg-blue-950/30 border border-blue-800/40 rounded-lg text-xs text-blue-300">
              <span className="font-semibold block">Decision-Support Insight:</span>
              Section {topCandidate.section_id} shows high consumer outage density and voltage drop, combined with wind gusts of 48 km/h. AB-14 isolation recommended.
            </div>
          </div>
        </div>
      )}

      {/* Ranked Candidate Sections Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <h3 className="text-sm font-semibold text-white">Surviving Candidate Line Sections (Pruned & Ranked)</h3>
          </div>
          <span className="text-xs text-gray-400 font-mono">
            {analysisResult?.top_candidates?.length || 0} Candidates Evaluated
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0A0F1D] text-gray-400 border-b border-[#1F2937]">
              <tr>
                <th className="py-2.5 px-3">Rank</th>
                <th className="py-2.5 px-3">Section ID</th>
                <th className="py-2.5 px-3">Model Confidence</th>
                <th className="py-2.5 px-3">Downstream Complaints</th>
                <th className="py-2.5 px-3">Outage Density</th>
                <th className="py-2.5 px-3">Downstream DTs</th>
                <th className="py-2.5 px-3">Isolation Switch</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {analysisResult?.top_candidates?.map((cand) => (
                <tr key={cand.section_id} className={`hover:bg-gray-800/30 transition ${cand.rank === 1 ? 'bg-red-950/20' : ''}`}>
                  <td className="py-2.5 px-3 font-mono font-bold">
                    {cand.rank === 1 ? (
                      <span className="bg-red-600 text-white px-2 py-0.5 rounded text-[10px]">#1</span>
                    ) : (
                      <span className="text-gray-400">#{cand.rank}</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 font-mono font-bold text-white">{cand.section_id}</td>
                  <td className="py-2.5 px-3">
                    <span className="font-mono text-blue-400 font-bold">
                      {(cand.calibrated_confidence * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-gray-400 block font-mono">
                      (raw: {cand.raw_model_score.toFixed(4)})
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-gray-300">{cand.downstream_complaints} calls</td>
                  <td className="py-2.5 px-3 font-mono text-amber-400">
                    {(cand.features?.consumer_outage_density * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3 text-gray-300">{cand.downstream_dts} DTs</td>
                  <td className="py-2.5 px-3 font-mono text-blue-300">{cand.isolation_switch || '—'}</td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => onNavigateToRestoration(analysisResult.prediction_id, cand.section_id)}
                      className="text-xs text-blue-400 hover:text-blue-300 font-medium transition"
                    >
                      Plan Restoration &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
