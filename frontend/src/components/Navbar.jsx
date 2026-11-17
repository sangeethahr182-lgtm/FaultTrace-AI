import React from 'react';
import { 
  Zap, 
  LayoutDashboard, 
  Activity, 
  Map, 
  ShieldCheck, 
  Database, 
  BarChart3,
  AlertTriangle,
  Info
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'faults', label: 'Fault Intelligence', icon: Activity },
    { id: 'map', label: 'Network Map', icon: Map },
    { id: 'restoration', label: 'Restoration Advisory', icon: ShieldCheck },
    { id: 'data', label: 'Data Management', icon: Database },
    { id: 'analytics', label: 'Analytics & Calibration', icon: BarChart3 },
  ];

  return (
    <header className="bg-[#111827] border-b border-[#1F2937] sticky top-0 z-50">
      {/* Top Banner Notice: Non-Negotiable Rule 1 */}
      <div className="bg-amber-950/80 border-b border-amber-800/60 px-4 py-1.5 flex items-center justify-between text-xs text-amber-300">
        <div className="flex items-center space-x-2">
          <span className="bg-amber-500 text-black font-extrabold px-1.5 py-0.5 rounded text-[10px] tracking-wider uppercase">
            SYNTHETIC DEMO DATA
          </span>
          <span className="font-medium hidden sm:inline">
            BESCOM Power Hack 2026 – Theme 10 (Distribution Operations Transformation)
          </span>
          <span className="text-amber-400/80 hidden md:inline">
            • All network assets, coordinates, complaints, and SCADA events are simulated. No access to real BESCOM data.
          </span>
        </div>
        <div className="flex items-center space-x-1.5 text-amber-200">
          <Info className="w-3.5 h-3.5" />
          <span className="font-semibold text-[11px]">ADVISORY ONLY – Operator Authorisation Required</span>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('overview')}>
            <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6 text-blue-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">FaultTrace <span className="text-blue-400">AI</span></span>
                <span className="text-[10px] bg-blue-900/60 text-blue-300 font-semibold px-2 py-0.5 rounded-full border border-blue-700/50">
                  v1.0 Local
                </span>
              </div>
              <p className="text-[11px] text-gray-400">Decision-Support System for 11kV Radial Distribution</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex space-x-1 sm:space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 shadow-sm'
                      : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-gray-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
