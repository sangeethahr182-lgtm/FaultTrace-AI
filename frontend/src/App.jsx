import React, { useState } from 'react';
import Navbar from './components/Navbar';
import OverviewPage from './pages/OverviewPage';
import FaultIntelligencePage from './pages/FaultIntelligencePage';
import NetworkMapPage from './pages/NetworkMapPage';
import RestorationPage from './pages/RestorationPage';
import DataManagementPage from './pages/DataManagementPage';
import AnalyticsPage from './pages/AnalyticsPage';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedFeederId, setSelectedFeederId] = useState('F4');
  const [targetSectionId, setTargetSectionId] = useState('F4-S14');
  const [predictionId, setPredictionId] = useState('F4');

  const handleNavigateToFaults = (feederId = 'F4') => {
    setSelectedFeederId(feederId);
    setActiveTab('faults');
  };

  const handleNavigateToRestoration = (predId = 'F4', sectionId = 'F4-S14') => {
    setPredictionId(predId);
    setTargetSectionId(sectionId);
    setActiveTab('restoration');
  };

  return (
    <div className="min-h-screen bg-[#0A0F1D] text-gray-100 flex flex-col font-sans">
      {/* Top Navbar with Synthetic Banner */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Page Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'overview' && (
          <OverviewPage
            onNavigateToFaults={handleNavigateToFaults}
            onNavigateToRestoration={handleNavigateToRestoration}
          />
        )}

        {activeTab === 'faults' && (
          <FaultIntelligencePage
            selectedFeederId={selectedFeederId}
            onNavigateToRestoration={handleNavigateToRestoration}
          />
        )}

        {activeTab === 'map' && (
          <NetworkMapPage selectedFeederId={selectedFeederId} />
        )}

        {activeTab === 'restoration' && (
          <RestorationPage
            predictionId={predictionId}
            targetSectionId={targetSectionId}
          />
        )}

        {activeTab === 'data' && (
          <DataManagementPage />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsPage />
        )}
      </main>

      {/* Control Room Footer */}
      <footer className="bg-[#111827] border-t border-[#1F2937] py-4 text-xs text-gray-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-gray-200">FaultTrace AI</span>
            <span>• BESCOM Power Hack 2026 Theme 10 Decision-Support Prototype</span>
          </div>
          <div className="text-amber-400 text-[11px] font-medium text-center sm:text-right">
            SYNTHETIC DEMO DATA • Advisory Decision Support Only • No Switching Execution
          </div>
        </div>
      </footer>
    </div>
  );
}
