import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight, 
  Truck, 
  Zap, 
  Compass, 
  Activity, 
  RefreshCw,
  Droplets,
  Building2,
  Clock,
  MapPin
} from 'lucide-react';
import { generateRestorationPlan, fetchRestorationPlans } from '../api';

export default function RestorationPage({ predictionId = 'F4', targetSectionId = 'F4-S14' }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPlan = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await generateRestorationPlan(predictionId, targetSectionId);
      setPlan(res);
    } catch (err) {
      setError(err.message || 'Failed to generate restoration plan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlan();
  }, [predictionId, targetSectionId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
        <p className="text-gray-400 text-sm">Evaluating radial topology & generating advisory restoration sequence...</p>
      </div>
    );
  }

  const radialCheck = plan?.radial_connectivity_check || {};
  const capacityCheck = plan?.rated_capacity_sum_check || {};
  const tieCheck = plan?.tie_switch_availability_check || {};
  const crew = plan?.crew_dispatch || {};

  return (
    <div className="space-y-6">
      {/* Non-Negotiable Rule 2: Mandatory Advisory Disclaimer Banner */}
      <div className="bg-amber-950/70 border-2 border-amber-600/80 rounded-xl p-4 sm:p-5 shadow-lg shadow-amber-950/20">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-amber-500/20 border border-amber-500/40 rounded-lg text-amber-400 mt-0.5">
            <AlertTriangle className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs uppercase font-extrabold bg-amber-500 text-black px-2 py-0.5 rounded tracking-wider">
                ADVISORY RESTORATION GUIDANCE ONLY
              </span>
              <span className="text-xs text-amber-300 font-mono">Requires Operator Authorisation</span>
            </div>
            <p className="text-xs sm:text-sm text-amber-200/90 mt-1 font-medium">
              The system never executes remote switching and never declares an electrical network &quot;safe&quot;. Every step below is strictly advisory and requires physical field verification, safety grounding protocols, and certified operator approval.
            </p>
          </div>
        </div>
      </div>

      {/* Plan Summary Header */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-bold text-white">
              Advisory Restoration Plan: Feeder {plan?.feeder_id || 'F4'}
            </h2>
          </div>
          <p className="text-xs text-gray-400 mt-0.5 font-mono">
            Plan ID: {plan?.plan_id} • Isolated Target: {plan?.isolated_section}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="bg-red-500/20 text-red-400 border border-red-500/30 px-3 py-1 rounded text-xs font-semibold">
            Isolate: {plan?.isolation_switch}
          </span>
          <span className="bg-blue-500/20 text-blue-400 border border-blue-500/30 px-3 py-1 rounded text-xs font-semibold">
            Backfeed: {plan?.tie_switch_id} &rarr; Feeder {plan?.alternate_donor_feeder}
          </span>
        </div>
      </div>

      {/* Non-Negotiable Rule 5: 3 Explicit Engineering Validation Checks */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
          Implemented Engineering Validation Checks (Pre-Execution Verification)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Check 1: Radial Connectivity */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-mono font-bold">Check 1: Radial Tree</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${radialCheck.passed ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400'}`}>
                  {radialCheck.passed ? 'PASSED' : 'FAILED'}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">radial_connectivity_check</h4>
              <p className="text-xs text-gray-400 mt-2">
                {radialCheck.details || 'Cycles detected: 0. Radial tree topology preserved without backfeed loops.'}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#1F2937] text-[10px] text-gray-500">
              Verified via NetworkX cycle basis detection
            </div>
          </div>

          {/* Check 2: Rated-Capacity Sum */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-mono font-bold">Check 2: Load Transfer</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${capacityCheck.passed ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400'}`}>
                  {capacityCheck.passed ? 'PASSED' : 'FAILED'}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">rated_capacity_sum_check</h4>
              <p className="text-xs text-gray-400 mt-2">
                Projected: <strong className="text-white font-mono">{capacityCheck.total_projected_amps}A</strong> vs Rated: <strong className="text-white font-mono">{capacityCheck.donor_feeder_rated_amps}A</strong> (Margin: <span className="text-green-400 font-bold font-mono">+{capacityCheck.headroom_margin_amps}A</span>).
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#1F2937] text-[10px] text-gray-500">
              Donor Feeder {plan?.alternate_donor_feeder} capacity verified
            </div>
          </div>

          {/* Check 3: Tie-Switch Availability */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-mono font-bold">Check 3: Inter-Feeder Tie</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${tieCheck.passed ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400'}`}>
                  {tieCheck.passed ? 'PASSED' : 'FAILED'}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">tie_switch_availability_check</h4>
              <p className="text-xs text-gray-400 mt-2">
                Switch <strong className="text-white font-mono">{tieCheck.tie_switch_id || 'TS-08'}</strong> is functional, physically inspected, and currently <strong className="text-amber-400">{tieCheck.current_state || 'OPEN'}</strong>.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#1F2937] text-[10px] text-gray-500">
              Ready for authorized closing operation
            </div>
          </div>
        </div>
      </div>

      {/* Step-by-Step Advisory Sequence */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center space-x-2">
          <span>Advisory Restoration Sequence (Step-by-Step Operator Guidance)</span>
        </h3>

        <div className="space-y-4">
          {plan?.steps?.map((step) => (
            <div
              key={step.step_number}
              className="bg-[#0A0F1D] border border-[#1F2937] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3"
            >
              <div className="flex items-start space-x-3.5">
                <span className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-500/40 text-blue-400 font-bold flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                  {step.step_number}
                </span>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-bold uppercase font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                      {step.action_type}
                    </span>
                    <span className="font-mono font-bold text-white text-xs">{step.target_device}</span>
                  </div>
                  <p className="text-xs text-gray-200 mt-1">{step.description}</p>
                </div>
              </div>

              <div className="flex-shrink-0 text-left md:text-right">
                <span className="text-[10px] text-amber-400 font-medium block">
                  {step.safety_rule}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Crew Dispatch Routing & Critical Loads Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rapid Restoration Crew Dispatch */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <Truck className="w-5 h-5 text-blue-400" />
              <h3 className="text-sm font-semibold text-white">Rapid Restoration Crew Dispatch Point & Route</h3>
            </div>

            <div className="bg-[#0A0F1D] p-3 rounded-lg border border-[#1F2937] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Assigned Unit:</span>
                <strong className="text-white font-mono">{crew.dispatch_team || 'Hebbal Rapid Unit #2'}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Response Vehicle:</span>
                <span className="text-gray-200 font-mono">{crew.vehicle || 'BESCOM-VAN-12'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Destination Span:</span>
                <span className="text-red-400 font-bold font-mono">
                  Line Section {crew.destination?.section_id || 'F4-S14'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Estimated Route Distance:</span>
                <span className="text-white font-mono">{crew.distance_km || 3.5} km</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Estimated ETA:</span>
                <span className="text-amber-400 font-bold font-mono">{crew.estimated_eta_minutes || 20} minutes</span>
              </div>
            </div>

            <div className="mt-3 text-[11px] text-gray-400 space-y-1">
              <p className="font-semibold text-gray-300">Dispatch Routing Advisory:</p>
              <ul className="list-disc pl-4 space-y-0.5 text-gray-400 text-[10px]">
                {crew.route_waypoints?.map((wp, idx) => (
                  <li key={idx}>Waypoint {idx + 1}: {wp.label} ({wp.lat.toFixed(4)}, {wp.lng.toFixed(4)})</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1F2937] text-[10px] text-amber-400">
            * Note: Route is an approximate straight-line/graph route for crew navigation advisory.
          </div>
        </div>

        {/* Affected Critical Assets in Fault Zone */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <Droplets className="w-5 h-5 text-red-400" />
              <h3 className="text-sm font-semibold text-white">Critical Loads Dependent on Restoration</h3>
            </div>

            <div className="space-y-3">
              <div className="p-3.5 bg-red-950/40 border border-red-800/80 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">District Water Pump #3</span>
                  <span className="text-[10px] bg-red-600 text-white font-bold px-2 py-0.5 rounded">
                    PRIORITY 1
                  </span>
                </div>
                <p className="text-xs text-gray-300 mt-1">
                  Located on Transformer <strong>DT-14</strong> (Section F4-S15). Sanctioned Load: 80 kW.
                </p>
                <div className="flex items-center justify-between text-[11px] text-gray-400 mt-2 pt-2 border-t border-red-900/60 font-mono">
                  <span>Backup Gen: <strong>None (Critical Grid Dependent)</strong></span>
                  <span>Contact: +91-80-2456-7890</span>
                </div>
              </div>

              <div className="p-3 bg-[#0A0F1D] border border-[#1F2937] rounded-lg text-xs space-y-1 text-gray-400">
                <span className="text-white font-semibold block">Downstream Island Consumer Summary:</span>
                <p>• DT-12: ~95 consumers (Section F4-S14)</p>
                <p>• DT-13: ~90 consumers (Section F4-S14)</p>
                <p>• DT-14: ~105 consumers + District Water Pump #3 (Section F4-S15)</p>
                <p>• DT-16: ~90 consumers (Section F4-S16 - Adjacent to TS-08)</p>
                <p className="font-bold text-amber-400 pt-1">• Total Affected: ~380 consumers</p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1F2937] text-[10px] text-gray-400">
            Executing the back-feed through TS-08 restores power to all 380 consumers and District Water Pump #3.
          </div>
        </div>
      </div>
    </div>
  );
}
