import React, { useState, useEffect } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Polyline, 
  CircleMarker 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  MapPin, 
  Layers, 
  ShieldAlert, 
  Radio, 
  Activity, 
  Droplets, 
  Truck, 
  Zap,
  Info
} from 'lucide-react';
import { fetchTopology } from '../api';

// Custom icons using Lucide/SVG data URIs or standard divIcons
const createCustomIcon = (color, text) => {
  return L.divIcon({
    className: 'custom-div-icon',
    html: `
      <div style="background-color: ${color}; color: white; padding: 4px 6px; border-radius: 6px; font-size: 10px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.5); text-align: center; white-space: nowrap;">
        ${text}
      </div>
    `,
    iconSize: [60, 24],
    iconAnchor: [30, 12]
  });
};

export default function NetworkMapPage({ selectedFeederId = 'F4' }) {
  const [topology, setTopology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showDTs, setShowDTs] = useState(true);
  const [showSwitches, setShowSwitches] = useState(true);
  const [showCrewRoute, setShowCrewRoute] = useState(true);

  useEffect(() => {
    fetchTopology(selectedFeederId)
      .then(data => {
        setTopology(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedFeederId]);

  // Center coordinate around Bengaluru Hebbal / Manyata
  const centerPosition = [13.048, 77.606];

  // Approximate crew dispatch route from Hebbal Substation to F4-S14
  const crewRouteCoords = [
    [13.0358, 77.5970], // Hebbal Depot
    [13.0420, 77.6020], // Bellary Road
    [13.0480, 77.6060], // Nagawara Ring Road
    [13.0538, 77.6100], // Faulted Section F4-S14 Span
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <p className="text-gray-400 text-sm">Loading GIS distribution topology...</p>
      </div>
    );
  }

  const sections = topology?.nodes?.filter(n => n.type === 'SECTION') || [];
  const transformers = topology?.nodes?.filter(n => n.type === 'TRANSFORMER' || n.type === 'CRITICAL_LOAD') || [];
  const switches = topology?.nodes?.filter(n => n.type === 'SWITCH' || n.type === 'BREAKER') || [];
  const substation = topology?.nodes?.find(n => n.type === 'SUBSTATION');

  return (
    <div className="space-y-4">
      {/* Map Control Bar & Toggles */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Radio className="w-5 h-5 text-blue-400" />
            <h2 className="text-sm sm:text-base font-bold text-white">
              Feeder {topology?.feeder_code || 'F4'} Distribution GIS Network Map
            </h2>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Synthetic Coordinates • Hebbal 66/11kV Substation & Manyata Tech Park Feeder
          </p>
        </div>

        {/* Layer Toggles & Legend */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <label className="flex items-center space-x-1.5 cursor-pointer text-gray-300">
            <input
              type="checkbox"
              checked={showDTs}
              onChange={(e) => setShowDTs(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-blue-600 focus:ring-0"
            />
            <span>Show Transformers ({transformers.length})</span>
          </label>

          <label className="flex items-center space-x-1.5 cursor-pointer text-gray-300">
            <input
              type="checkbox"
              checked={showSwitches}
              onChange={(e) => setShowSwitches(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-blue-600 focus:ring-0"
            />
            <span>Show Switches (AB & Tie)</span>
          </label>

          <label className="flex items-center space-x-1.5 cursor-pointer text-gray-300">
            <input
              type="checkbox"
              checked={showCrewRoute}
              onChange={(e) => setShowCrewRoute(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-amber-500 focus:ring-0"
            />
            <span>Crew Dispatch Route</span>
          </label>
        </div>
      </div>

      {/* Map & Detail Split Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Map Container */}
        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden h-[620px] relative">
          <MapContainer
            center={centerPosition}
            zoom={14}
            scrollWheelZoom={true}
            style={{ height: '100%', width: '100%' }}
          >
            {/* OpenStreetMap Dark / Standard CartoDB Tile */}
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {/* Substation Marker */}
            {substation && (
              <Marker
                position={[substation.lat, substation.lng]}
                icon={createCustomIcon('#2563EB', 'SUB-01')}
                eventHandlers={{ click: () => setSelectedNode(substation) }}
              >
                <Popup>
                  <div className="text-xs">
                    <strong className="block text-sm">{substation.label}</strong>
                    <p className="text-gray-400">Capacity: 50 MVA 66/11kV</p>
                  </div>
                </Popup>
              </Marker>
            )}

            {/* 11kV Line Sections Polylines */}
            {sections.map((sec) => {
              const start = sec.metadata?.start_coords || [sec.lat - 0.002, sec.lng - 0.001];
              const end = sec.metadata?.end_coords || [sec.lat, sec.lng];
              
              let lineColor = '#10B981'; // ENERGIZED (Green)
              if (sec.id === 'F4-S14') {
                lineColor = '#EF4444'; // FAULTED (Red)
              } else if (sec.status === 'DE_ENERGIZED' || ['F4-S15', 'F4-S16'].includes(sec.id)) {
                lineColor = '#F59E0B'; // DE_ENERGIZED downstream island (Amber)
              }

              return (
                <Polyline
                  key={sec.id}
                  positions={[start, end]}
                  color={lineColor}
                  weight={sec.id === 'F4-S14' ? 6 : 4}
                  opacity={0.9}
                  eventHandlers={{ click: () => setSelectedNode(sec) }}
                >
                  <Popup>
                    <div className="text-xs">
                      <strong className="text-sm block">{sec.id}</strong>
                      <p>Length: {sec.metadata?.length_km} km</p>
                      <p>Conductor: {sec.metadata?.conductor}</p>
                      <p>Status: <span className="font-bold">{sec.status}</span></p>
                    </div>
                  </Popup>
                </Polyline>
              );
            })}

            {/* Distribution Transformers */}
            {showDTs && transformers.map((dt) => {
              const isCrit = dt.metadata?.is_critical;
              const isDeenergized = dt.status === 'DE_ENERGIZED';
              
              let fillColor = '#3B82F6';
              if (isCrit) fillColor = '#EC4899'; // Pink for Hospital/Water pump
              else if (isDeenergized) fillColor = '#EF4444';

              return (
                <CircleMarker
                  key={dt.id}
                  center={[dt.lat, dt.lng]}
                  radius={isCrit ? 9 : 6}
                  fillColor={fillColor}
                  color="#FFFFFF"
                  weight={1.5}
                  opacity={1}
                  fillOpacity={0.85}
                  eventHandlers={{ click: () => setSelectedNode(dt) }}
                >
                  <Popup>
                    <div className="text-xs">
                      <strong className="block text-sm">{dt.label}</strong>
                      <p>Rating: {dt.metadata?.capacity_kva} kVA</p>
                      <p>Status: <span className="font-bold">{dt.status}</span></p>
                      {isCrit && (
                        <p className="text-red-400 font-bold mt-1">
                          CRITICAL ASSET: {dt.metadata?.critical_name}
                        </p>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {/* Switches (AB-14, TS-08, CB-F4) */}
            {showSwitches && switches.map((sw) => {
              const isTie = sw.metadata?.switch_type === 'TIE_SWITCH';
              const isBreaker = sw.metadata?.switch_type === 'BREAKER';
              const iconColor = isTie ? '#F59E0B' : (isBreaker ? '#3B82F6' : '#8B5CF6');

              return (
                <Marker
                  key={sw.id}
                  position={[sw.lat, sw.lng]}
                  icon={createCustomIcon(iconColor, sw.id)}
                  eventHandlers={{ click: () => setSelectedNode(sw) }}
                >
                  <Popup>
                    <div className="text-xs">
                      <strong className="block text-sm">{sw.label}</strong>
                      <p>Type: {sw.metadata?.switch_type}</p>
                      <p>Normal: {sw.metadata?.normal_state} | Current: {sw.metadata?.current_state}</p>
                      {isTie && (
                        <p className="text-amber-400 font-semibold mt-1">
                          Tie Switch to Feeder {sw.metadata?.adjacent_feeder_id}
                        </p>
                      )}
                    </div>
                  </Popup>
                </Marker>
              );
            })}

            {/* Crew Dispatch Route Polyline */}
            {showCrewRoute && (
              <Polyline
                positions={crewRouteCoords}
                color="#38BDF8"
                dashArray="6, 8"
                weight={3}
                opacity={0.8}
              >
                <Popup>
                  <div className="text-xs">
                    <strong>Rapid Restoration Crew Route</strong>
                    <p className="text-gray-400">Advisory route from Depot to F4-S14 (~3.5 km)</p>
                  </div>
                </Popup>
              </Polyline>
            )}
          </MapContainer>

          {/* Map Overlay Badge */}
          <div className="absolute bottom-3 left-3 bg-[#0A0F1D]/90 border border-[#1F2937] rounded-lg p-2.5 text-[11px] text-gray-300 space-y-1 z-[1000] pointer-events-auto">
            <div className="flex items-center space-x-2">
              <span className="w-3 h-1 bg-green-500 rounded" />
              <span>Energized 11kV Trunk</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-1.5 bg-red-500 rounded" />
              <span>Faulted Section (F4-S14)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-1 bg-amber-500 rounded" />
              <span>De-Energized Downstream Island</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-pink-500" />
              <span>Critical Load (Hospital / Water Pump)</span>
            </div>
          </div>
        </div>

        {/* Element Inspection Drawer */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-[#1F2937]">
              <Info className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-white">Element Inspector</h3>
            </div>

            {selectedNode ? (
              <div className="mt-4 space-y-3 text-xs">
                <div>
                  <span className="text-gray-400 block">Identifier</span>
                  <strong className="text-base font-bold text-white font-mono">{selectedNode.id}</strong>
                  <span className="text-[11px] text-gray-400">{selectedNode.label}</span>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-[#0A0F1D] p-2.5 rounded-lg border border-[#1F2937]">
                  <div>
                    <span className="text-gray-400 text-[10px]">Type</span>
                    <strong className="block text-blue-400">{selectedNode.type}</strong>
                  </div>
                  <div>
                    <span className="text-gray-400 text-[10px]">Status</span>
                    <strong className={`block ${selectedNode.status === 'FAULTED' ? 'text-red-400' : (selectedNode.status === 'ENERGIZED' ? 'text-green-400' : 'text-amber-400')}`}>
                      {selectedNode.status}
                    </strong>
                  </div>
                </div>

                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Coordinates:</span>
                    <span className="font-mono text-gray-200">{selectedNode.lat.toFixed(4)}, {selectedNode.lng.toFixed(4)}</span>
                  </div>
                  {selectedNode.metadata?.length_km && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Span Length:</span>
                      <span className="text-gray-200">{selectedNode.metadata.length_km} km</span>
                    </div>
                  )}
                  {selectedNode.metadata?.capacity_kva && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Transformer Rating:</span>
                      <span className="text-gray-200">{selectedNode.metadata.capacity_kva} kVA</span>
                    </div>
                  )}
                  {selectedNode.metadata?.is_critical && (
                    <div className="p-2 bg-red-950/40 border border-red-800 rounded text-red-300 font-semibold mt-2">
                      Critical Load: {selectedNode.metadata.critical_name}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-gray-500">
                Click any line section, transformer, or switch on the map to inspect its electrical telemetry.
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-[#1F2937] text-[11px] text-gray-400">
            <span className="text-amber-400 font-medium">GIS Note: </span>
            Coordinates are synthetic approximations simulating North Bengaluru distribution feeder paths.
          </div>
        </div>
      </div>
    </div>
  );
}
