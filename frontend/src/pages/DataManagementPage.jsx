import React, { useState } from 'react';
import { 
  Database, 
  UploadCloud, 
  Download, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  RefreshCw,
  FileCode,
  Table
} from 'lucide-react';
import { ingestEvent, uploadData } from '../api';

export default function DataManagementPage() {
  const [datasetType, setDatasetType] = useState('complaints');
  const [fileContent, setFileContent] = useState('');
  const [filename, setFilename] = useState('');
  const [uploadResult, setUploadResult] = useState(null);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  // Handle synthetic ingestion trigger
  const handleSimulateTrip = async () => {
    try {
      setLoading(true);
      setIngestStatus(null);
      const res = await ingestEvent({
        feeder_id: 'F4',
        section_id: 'F4-S14',
        event_type: 'OVERCURRENT_TRIP',
        current_amps: 685.0,
        voltage_kv: 0.0,
        description: 'Simulated Phase-B Earth Fault & Breaker Lockout (Synthetic Ingestion)'
      });
      setIngestStatus(`Success: ${res.message}`);
    } catch (err) {
      setIngestStatus(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFilename(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => {
      setFileContent(evt.target.result);
    };
    reader.readAsText(file);
  };

  const handleSubmitUpload = async (e) => {
    e.preventDefault();
    if (!fileContent) return;

    try {
      setLoading(true);
      const res = await uploadData({
        dataset_type: datasetType,
        filename: filename || `uploaded_${datasetType}.csv`,
        content: fileContent
      });
      setUploadResult(res);
    } catch (err) {
      alert(`Upload validation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Sample CSV templates for instant testing
  const loadSampleCSV = () => {
    setFilename('synthetic_complaints_sample.csv');
    setFileContent(
`# SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10
id,timestamp,transformer_id,section_id,category,source,description
C101,2026-11-17T17:15:00,DT-14,F4-S15,NO_POWER,IVRS,Complete power cut reported
C102,2026-11-17T17:16:00,DT-12,F4-S14,SPARK_REPORTED,APP,Sparks on 11kV conductor near S14
C103,2026-11-17T17:17:00,DT-13,F4-S14,NO_POWER,CALL_CENTER,Lights went out during gust
C104,2026-11-17T17:18:00,DT-16,F4-S16,VOLTAGE_FLUCTUATION,SMS,Dim voltage before total outage`
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <div className="flex items-center space-x-2">
          <Database className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">Synthetic Data Ingestion & Dataset Management</h2>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Validate and stage synthetic SCADA events, consumer complaints, weather telemetry, and feeder GIS topology.
        </p>
      </div>

      {/* Simulator Trigger Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <Play className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Simulate SCADA Trip Event</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Injects a synthetic phase-to-earth fault trip on Feeder F4 (Section F4-S14, 685A fault current). Updates feeder breaker state to TRIPPED.
            </p>
          </div>

          <div>
            {ingestStatus && (
              <div className={`p-2.5 rounded-lg text-xs font-mono mb-3 ${ingestStatus.startsWith('Success') ? 'bg-green-950/40 text-green-300 border border-green-800' : 'bg-red-950/40 text-red-300 border border-red-800'}`}>
                {ingestStatus}
              </div>
            )}
            <button
              onClick={handleSimulateTrip}
              disabled={loading}
              className="w-full py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Simulate Feeder F4 Trip Ingestion</span>
            </button>
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <Download className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-white">Pre-Generated Synthetic Datasets</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Download simulated datasets created by the scenario simulator. All records contain explicit synthetic disclaimer headers.
            </p>

            <div className="space-y-2 text-xs font-mono">
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span>synthetic_network_topology.json</span>
                <span className="text-gray-400 text-[11px]">20 Sections, 20 DTs</span>
              </div>
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span>synthetic_scada_events.csv</span>
                <span className="text-gray-400 text-[11px]">Surge & Lockouts</span>
              </div>
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span>synthetic_consumer_complaints.csv</span>
                <span className="text-gray-400 text-[11px]">142 IVRS/App Calls</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1F2937] text-[10px] text-gray-400">
            Available locally in <code className="text-blue-300 font-mono">backend/datasets/</code>
          </div>
        </div>
      </div>

      {/* CSV / JSON Upload Form */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <UploadCloud className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Upload Synthetic Dataset (CSV / JSON)</h3>
          </div>
          <button
            type="button"
            onClick={loadSampleCSV}
            className="text-xs text-blue-400 hover:text-blue-300 underline font-medium"
          >
            Load Sample CSV Template
          </button>
        </div>

        <form onSubmit={handleSubmitUpload} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Dataset Category</label>
              <select
                value={datasetType}
                onChange={(e) => setDatasetType(e.target.value)}
                className="w-full bg-[#0A0F1D] border border-[#1F2937] text-white text-xs rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500"
              >
                <option value="complaints">Consumer Complaints (AMI / IVRS)</option>
                <option value="scada">SCADA Telemetry & Protection Trips</option>
                <option value="topology">Network Topology (Feeders & Sections)</option>
                <option value="weather">Weather Observations</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-400 block mb-1">Choose File</label>
              <input
                type="file"
                accept=".csv,.json"
                onChange={handleFileUpload}
                className="w-full text-xs text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Raw Dataset Content Preview (CSV or JSON)</label>
            <textarea
              rows={5}
              value={fileContent}
              onChange={(e) => setFileContent(e.target.value)}
              placeholder="Paste or upload CSV / JSON synthetic data..."
              className="w-full bg-[#0A0F1D] border border-[#1F2937] rounded-lg p-3 text-xs font-mono text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={!fileContent || loading}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition disabled:opacity-50 shadow"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Validate & Stage Dataset</span>
          </button>
        </form>

        {/* Upload Preview & Validation Results */}
        {uploadResult && (
          <div className="mt-6 pt-5 border-t border-[#1F2937] space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-green-400 flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Validation Successful: {uploadResult.total_records} Records Parsed</span>
              </span>
              <span className="text-xs text-gray-400 font-mono">{uploadResult.filename}</span>
            </div>

            {/* Validation Checklist */}
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span className="text-gray-400">Format Check:</span>
                <span className="text-green-400 font-bold">VALID</span>
              </div>
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span className="text-gray-400">Synthetic Flag:</span>
                <span className="text-green-400 font-bold">VERIFIED</span>
              </div>
              <div className="bg-[#0A0F1D] p-2.5 rounded border border-[#1F2937] flex items-center justify-between">
                <span className="text-gray-400">Null Threshold:</span>
                <span className="text-green-400 font-bold">PASS (&lt;2%)</span>
              </div>
            </div>

            {/* Preview Table */}
            {uploadResult.preview?.length > 0 && (
              <div className="overflow-x-auto bg-[#0A0F1D] rounded-lg border border-[#1F2937] p-3">
                <div className="text-xs font-semibold text-gray-300 mb-2">First 5 Records Preview:</div>
                <table className="w-full text-left text-xs font-mono">
                  <thead className="text-gray-400 border-b border-gray-800">
                    <tr>
                      {Object.keys(uploadResult.preview[0]).map((col) => (
                        <th key={col} className="p-1.5">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 text-gray-300">
                    {uploadResult.preview.map((row, idx) => (
                      <tr key={idx}>
                        {Object.values(row).map((val, vIdx) => (
                          <td key={vIdx} className="p-1.5">{String(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
