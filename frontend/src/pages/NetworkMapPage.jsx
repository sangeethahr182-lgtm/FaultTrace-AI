import React, { useState, useEffect, useRef } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Polyline, 
  CircleMarker,
  Circle,
  useMap,
  useMapEvents
} from 'react-leaflet';
import L from 'leaflet';
import { 
  MapPin, 
  Layers, 
  ShieldAlert, 
  Radio, 
  Droplets, 
  Truck, 
  Zap,
  Info,
  Crosshair,
  Navigation,
  Compass,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  LocateFixed,
  Search,
  ExternalLink
} from 'lucide-react';
import { fetchTopology, fetchNearestAssetByGPS } from '../api';

// Custom icons
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

const createGpsTargetIcon = (label) => {
  return L.divIcon({
    className: 'gps-target-div',
    html: `
      <div style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;">
        <span class="gps-pulse-ring" style="position: absolute; width: 32px; height: 32px; border-radius: 9999px; background: rgba(59, 130, 246, 0.45);"></span>
        <span style="position: absolute; width: 18px; height: 18px; border-radius: 9999px; background: #2563EB; border: 2.5px solid #FFFFFF; box-shadow: 0 0 10px #3B82F6;"></span>
        <span style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); background: #1E3A8A; color: #BFDBFE; font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 4px; border: 1px solid #3B82F6; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">
          📍 ${label || 'GPS'}
        </span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17]
  });
};

const createCrewIcon = (label) => {
  return L.divIcon({
    className: 'crew-van-div',
    html: `
      <div style="background: #F59E0B; color: #111827; border: 2px solid #FFFFFF; border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 800; box-shadow: 0 2px 8px rgba(0,0,0,0.6); display: flex; align-items: center; gap: 4px; white-space: nowrap;">
        🚚 <span>${label || 'CREW'}</span>
      </div>
    `,
    iconSize: [88, 24],
    iconAnchor: [44, 12]
  });
};

// Leaflet Map Camera Controller
function MapRecenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.flyTo(center, zoom || 15, { duration: 1.2 });
    }
  }, [center, zoom, map]);
  return null;
}

// Leaflet Map Click Handler for GPS Picking
function MapClickHandler({ onMapClick, enabled }) {
  useMapEvents({
    click(e) {
      if (enabled) {
        onMapClick([e.latlng.lat, e.latlng.lng]);
      }
    }
  });
  return null;
}

// Great circle distance (Haversine)
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

const GPS_PRESETS = [
  { label: 'Suspected Fault Span (F4-S14)', lat: 13.0538, lng: 77.6100, desc: 'Heavy-rain flashover location' },
  { label: 'Substation SUB-01 (Hebbal 66/11kV)', lat: 13.0358, lng: 77.5970, desc: 'Source 50 MVA Substation' },
  { label: 'District Water Pump #3 (DT-14)', lat: 13.0521, lng: 77.6085, desc: 'Critical municipal water supply' },
  { label: 'Lifeline Hospital (DT-08)', lat: 13.0450, lng: 77.6040, desc: 'Critical hospital healthcare facility' },
  { label: 'Tie Switch TS-08 (To Feeder F3)', lat: 13.0550, lng: 77.6120, desc: 'Alternate back-feed interconnection' },
  { label: 'Air-Break Switch AB-14', lat: 13.0530, lng: 77.6095, desc: 'Fault isolation switch' },
  { label: 'Rapid Restoration Depot', lat: 13.0358, lng: 77.5970, desc: 'Crew staging and dispatch base' }
];

export default function NetworkMapPage({ selectedFeederId = 'F4' }) {
  const [topology, setTopology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showDTs, setShowDTs] = useState(true);
  const [showSwitches, setShowSwitches] = useState(true);
  const [showCrewRoute, setShowCrewRoute] = useState(true);

  // GPS State
  const [gpsCoords, setGpsCoords] = useState([13.0538, 77.6100]); // Default centered on F4-S14
  const [gpsLabel, setGpsLabel] = useState('Fault Span F4-S14');
  const [gpsAccuracyMeters, setGpsAccuracyMeters] = useState(15);
  const [inputLat, setInputLat] = useState('13.0538');
  const [inputLng, setInputLng] = useState('77.6100');
  const [isLocating, setIsLocating] = useState(false);
  const [gpsError, setGpsError] = useState(null);
  const [mapClickMode, setMapClickMode] = useState(false);
  const [nearestData, setNearestData] = useState(null);
  const [nearestLoading, setNearestLoading] = useState(false);
  const [mapCenterTarget, setMapCenterTarget] = useState([13.048, 77.606]);
  const [mapZoomTarget, setMapZoomTarget] = useState(14);

  // Crew GPS Telemetry Simulator
  const [crewPosIndex, setCrewPosIndex] = useState(0);
  const [isCrewSimulating, setIsCrewSimulating] = useState(false);
  const crewSimTimerRef = useRef(null);

  // Crew dispatch route coordinates
  const crewRouteCoords = [
    [13.0358, 77.5970], // Hebbal Depot
    [13.0400, 77.6000], // Bellary Road South
    [13.0440, 77.6030], // Bellary Road Mid
    [13.0480, 77.6060], // Outer Ring Road Junction
    [13.0510, 77.6080], // Manyata Link
    [13.0538, 77.6100]  // Faulted Section F4-S14
  ];

  // Load topology
  useEffect(() => {
    setLoading(true);
    fetchTopology(selectedFeederId)
      .then(data => {
        setTopology(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedFeederId]);

  // Query nearest assets when GPS changes
  useEffect(() => {
    if (gpsCoords && gpsCoords[0] && gpsCoords[1]) {
      setNearestLoading(true);
      fetchNearestAssetByGPS(selectedFeederId, gpsCoords[0], gpsCoords[1])
        .then(data => {
          setNearestData(data);
          setNearestLoading(false);
        })
        .catch(() => setNearestLoading(false));
    }
  }, [gpsCoords, selectedFeederId]);

  // Crew Simulation loop
  useEffect(() => {
    if (isCrewSimulating) {
      crewSimTimerRef.current = setInterval(() => {
        setCrewPosIndex(prev => {
          if (prev >= crewRouteCoords.length - 1) {
            setIsCrewSimulating(false);
            return prev;
          }
          return prev + 1;
        });
      }, 2500);
    } else {
      clearInterval(crewSimTimerRef.current);
    }
    return () => clearInterval(crewSimTimerRef.current);
  }, [isCrewSimulating]);

  // Request browser GPS location
  const handleGetDeviceLocation = () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }
    setIsLocating(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy || 20;

        setGpsCoords([lat, lng]);
        setGpsLabel('Live Device GPS');
        setGpsAccuracyMeters(Math.round(accuracy));
        setInputLat(lat.toFixed(6));
        setInputLng(lng.toFixed(6));
        setMapCenterTarget([lat, lng]);
        setMapZoomTarget(16);
        setIsLocating(false);
      },
      (error) => {
        setIsLocating(false);
        setGpsError(`GPS Access Error: ${error.message}. You can manually enter coordinates below.`);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  // Submit manual GPS coordinate form
  const handleManualGpsSubmit = (e) => {
    e?.preventDefault();
    const lat = parseFloat(inputLat);
    const lng = parseFloat(inputLng);

    if (isNaN(lat) || isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      setGpsError('Please enter valid Latitude (-90 to 90) and Longitude (-180 to 180).');
      return;
    }

    setGpsError(null);
    setGpsCoords([lat, lng]);
    setGpsLabel(`Target (${lat.toFixed(4)}, ${lng.toFixed(4)})`);
    setMapCenterTarget([lat, lng]);
    setMapZoomTarget(15);
  };

  // Select GPS preset
  const handleSelectPreset = (preset) => {
    setGpsError(null);
    setInputLat(preset.lat.toString());
    setInputLng(preset.lng.toString());
    setGpsCoords([preset.lat, preset.lng]);
    setGpsLabel(preset.label);
    setMapCenterTarget([preset.lat, preset.lng]);
    setMapZoomTarget(16);
  };

  // Handle map click to drop GPS pin
  const handleMapClick = (coords) => {
    setInputLat(coords[0].toFixed(6));
    setInputLng(coords[1].toFixed(6));
    setGpsCoords([coords[0], coords[1]]);
    setGpsLabel(`Map Click (${coords[0].toFixed(4)}, ${coords[1].toFixed(4)})`);
    setGpsError(null);
  };

  const sections = topology?.nodes?.filter(n => n.type === 'SECTION') || [];
  const transformers = topology?.nodes?.filter(n => n.type === 'TRANSFORMER' || n.type === 'CRITICAL_LOAD') || [];
  const switches = topology?.nodes?.filter(n => n.type === 'SWITCH' || n.type === 'BREAKER') || [];
  const substation = topology?.nodes?.find(n => n.type === 'SUBSTATION');

  const currentCrewCoords = crewRouteCoords[crewPosIndex];
  const distRemainingToFault = haversineKm(currentCrewCoords[0], currentCrewCoords[1], 13.0538, 77.6100);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <p className="text-gray-400 text-sm">Loading GIS distribution topology and GPS services...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* GPS Control Bar & Toolbar */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Navigation className="w-5 h-5 text-blue-400" />
              <h2 className="text-sm sm:text-base font-bold text-white">
                Feeder {topology?.feeder_code || 'F4'} GPS GIS Network & Dispatch Radar
              </h2>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Live GPS Geolocation • Reverse GPS Proximity • Real-Time Field Crew Telemetry
            </p>
          </div>

          {/* Quick GPS Geolocation & Click Mode Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleGetDeviceLocation}
              disabled={isLocating}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                isLocating 
                  ? 'bg-blue-900/50 text-blue-300 border border-blue-700 animate-pulse' 
                  : 'bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-900/40'
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span>{isLocating ? 'Acquiring GPS...' : 'Use My GPS Location'}</span>
            </button>

            <button
              onClick={() => setMapClickMode(!mapClickMode)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                mapClickMode 
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/50' 
                  : 'bg-[#0A0F1D] text-gray-300 border-[#1F2937] hover:border-gray-600'
              }`}
            >
              <LocateFixed className="w-3.5 h-3.5 text-amber-400" />
              <span>{mapClickMode ? 'Click Map Enabled (Active)' : 'Click Map to Pick GPS'}</span>
            </button>

            {/* Presets dropdown */}
            <div className="relative">
              <select
                onChange={(e) => {
                  const preset = GPS_PRESETS.find(p => p.label === e.target.value);
                  if (preset) handleSelectPreset(preset);
                }}
                defaultValue=""
                className="bg-[#0A0F1D] border border-[#1F2937] text-gray-200 text-xs rounded-lg px-2.5 py-1.5 focus:border-blue-500 focus:outline-none"
              >
                <option value="" disabled>⚡ Jump to GPS Waypoint...</option>
                {GPS_PRESETS.map((p, idx) => (
                  <option key={idx} value={p.label}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Manual GPS Coordinates Input Form */}
        <form onSubmit={handleManualGpsSubmit} className="pt-2 border-t border-[#1F2937] flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            <Search className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-medium text-gray-300">Custom GPS Coordinates:</span>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-[#0A0F1D] border border-[#1F2937] rounded-lg px-2.5 py-1 text-xs">
              <span className="text-gray-400 text-[11px] mr-1.5">Lat:</span>
              <input
                type="text"
                value={inputLat}
                onChange={(e) => setInputLat(e.target.value)}
                placeholder="13.0538"
                className="bg-transparent text-white w-24 outline-none font-mono"
              />
            </div>

            <div className="flex items-center bg-[#0A0F1D] border border-[#1F2937] rounded-lg px-2.5 py-1 text-xs">
              <span className="text-gray-400 text-[11px] mr-1.5">Lng:</span>
              <input
                type="text"
                value={inputLng}
                onChange={(e) => setInputLng(e.target.value)}
                placeholder="77.6100"
                className="bg-transparent text-white w-24 outline-none font-mono"
              />
            </div>

            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded-lg text-xs font-semibold transition"
            >
              Pinpoint GPS
            </button>
          </div>

          {/* Active GPS Status Badge */}
          <div className="ml-auto flex items-center space-x-2 text-xs">
            <span className="text-gray-400">Active GPS Target:</span>
            <span className="bg-blue-950/60 border border-blue-800 text-blue-300 px-2.5 py-0.5 rounded-full font-mono text-[11px]">
              {gpsCoords[0].toFixed(5)}, {gpsCoords[1].toFixed(5)}
            </span>
          </div>
        </form>

        {gpsError && (
          <div className="bg-red-950/40 border border-red-800/80 rounded-lg p-2 text-xs text-red-300 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{gpsError}</span>
          </div>
        )}
      </div>

      {/* Layer Toggles & Crew Telemetry Bar */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Layer Visibility */}
        <div className="flex items-center space-x-4 text-gray-300">
          <span className="text-gray-400 text-[11px] uppercase tracking-wider font-semibold">GIS Layers:</span>
          <label className="flex items-center space-x-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showDTs}
              onChange={(e) => setShowDTs(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-blue-600 focus:ring-0"
            />
            <span>Transformers ({transformers.length})</span>
          </label>

          <label className="flex items-center space-x-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showSwitches}
              onChange={(e) => setShowSwitches(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-blue-600 focus:ring-0"
            />
            <span>Switches ({switches.length})</span>
          </label>

          <label className="flex items-center space-x-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showCrewRoute}
              onChange={(e) => setShowCrewRoute(e.target.checked)}
              className="rounded bg-[#0A0F1D] border-gray-700 text-amber-500 focus:ring-0"
            />
            <span>Crew Dispatch Route</span>
          </label>
        </div>

        {/* Crew Simulator Controls */}
        <div className="flex items-center space-x-3 bg-[#0A0F1D] border border-[#1F2937] rounded-lg px-3 py-1">
          <Truck className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-gray-300 font-medium">Crew GPS Telemetry:</span>
          <span className="font-mono text-amber-300">
            {distRemainingToFault < 0.1 ? 'ARRIVED AT FAULT' : `${distRemainingToFault.toFixed(2)} km remaining`}
          </span>

          <div className="flex items-center space-x-1 ml-2">
            {!isCrewSimulating ? (
              <button
                onClick={() => setIsCrewSimulating(true)}
                disabled={crewPosIndex >= crewRouteCoords.length - 1}
                title="Play simulated GPS movement"
                className="p-1 hover:bg-[#1F2937] rounded text-green-400 disabled:opacity-30"
              >
                <Play className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={() => setIsCrewSimulating(false)}
                title="Pause simulation"
                className="p-1 hover:bg-[#1F2937] rounded text-amber-400"
              >
                <Pause className="w-3.5 h-3.5" />
              </button>
            )}

            <button
              onClick={() => {
                setIsCrewSimulating(false);
                setCrewPosIndex(0);
              }}
              title="Reset crew to Depot"
              className="p-1 hover:bg-[#1F2937] rounded text-gray-400 hover:text-white"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Map & Detail Split Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Map Container */}
        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden h-[630px] relative">
          <MapContainer
            center={mapCenterTarget}
            zoom={mapZoomTarget}
            scrollWheelZoom={true}
            style={{ height: '100%', width: '100%' }}
          >
            {/* Map Camera Controller */}
            <MapRecenter center={mapCenterTarget} zoom={mapZoomTarget} />

            {/* Map Click Event Handler */}
            <MapClickHandler onMapClick={handleMapClick} enabled={mapClickMode} />

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
                    <p className="font-mono text-[11px] text-blue-400 mt-1">GPS: {substation.lat.toFixed(4)}, {substation.lng.toFixed(4)}</p>
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
                      <p className="font-mono text-[11px] text-gray-400 mt-1">
                        GPS Mid: {((start[0] + end[0]) / 2).toFixed(4)}, {((start[1] + end[1]) / 2).toFixed(4)}
                      </p>
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
                      <p className="font-mono text-[11px] text-gray-400 mt-0.5">GPS: {dt.lat.toFixed(4)}, {dt.lng.toFixed(4)}</p>
                      {isCrit && (
                        <p className="text-pink-400 font-bold mt-1">
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
                      <p>State: {sw.metadata?.current_state}</p>
                      <p className="font-mono text-[11px] text-gray-400 mt-0.5">GPS: {sw.lat.toFixed(4)}, {sw.lng.toFixed(4)}</p>
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

            {/* Animated Field Crew Van Marker */}
            {showCrewRoute && (
              <Marker
                position={currentCrewCoords}
                icon={createCrewIcon('VAN-12')}
              >
                <Popup>
                  <div className="text-xs">
                    <strong className="block text-amber-400">Restoration Crew: BESCOM-VAN-12</strong>
                    <p className="text-gray-300">Hebbal Rapid Restoration Unit #2</p>
                    <p className="font-mono text-[11px] text-gray-400 mt-1">
                      GPS: {currentCrewCoords[0].toFixed(5)}, {currentCrewCoords[1].toFixed(5)}
                    </p>
                    <p className="text-amber-300 font-semibold mt-1">
                      Distance to Fault: {distRemainingToFault.toFixed(2)} km
                    </p>
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Active GPS Target Pinpoint Marker & Accuracy Circle */}
            {gpsCoords && (
              <>
                <Marker
                  position={gpsCoords}
                  icon={createGpsTargetIcon(gpsLabel)}
                >
                  <Popup>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-blue-400 block">GPS Point: {gpsLabel}</strong>
                      <p className="font-mono text-gray-300">Lat: {gpsCoords[0].toFixed(6)}</p>
                      <p className="font-mono text-gray-300">Lng: {gpsCoords[1].toFixed(6)}</p>
                      <p className="text-gray-400">Accuracy: ±{gpsAccuracyMeters}m</p>
                      {nearestData?.nearest_asset && (
                        <div className="mt-1 pt-1 border-t border-gray-700">
                          <span className="text-gray-400">Nearest Asset: </span>
                          <strong className="text-white">{nearestData.nearest_asset.label}</strong>
                          <span className="text-blue-300 font-mono block">
                            ({nearestData.nearest_asset.distance_meters}m away)
                          </span>
                        </div>
                      )}
                    </div>
                  </Popup>
                </Marker>

                {/* GPS Accuracy/Proximity Circle */}
                <Circle
                  center={gpsCoords}
                  radius={gpsAccuracyMeters * 3}
                  pathOptions={{
                    color: '#3B82F6',
                    fillColor: '#3B82F6',
                    fillOpacity: 0.12,
                    weight: 1.5,
                    dashArray: '4, 6'
                  }}
                />

                {/* Dashed line to nearest asset */}
                {nearestData?.nearest_asset && (
                  <Polyline
                    positions={[
                      gpsCoords,
                      [nearestData.nearest_asset.lat, nearestData.nearest_asset.lng]
                    ]}
                    color="#60A5FA"
                    dashArray="3, 6"
                    weight={2}
                    opacity={0.7}
                  />
                )}
              </>
            )}
          </MapContainer>

          {/* Map Overlay Badge & HUD */}
          <div className="absolute bottom-3 left-3 bg-[#0A0F1D]/90 backdrop-blur-sm border border-[#1F2937] rounded-lg p-2.5 text-[11px] text-gray-300 space-y-1 z-[1000] pointer-events-auto">
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
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 border border-white" />
              <span>Active GPS Target Pin</span>
            </div>
          </div>

          {/* Click to pick GPS indicator banner */}
          {mapClickMode && (
            <div className="absolute top-3 left-1/2 transform -translate-x-1/2 bg-amber-500 text-black px-4 py-1 rounded-full text-xs font-bold shadow-lg z-[1000] animate-bounce">
              Click anywhere on the map to place GPS pin
            </div>
          )}
        </div>

        {/* GPS Proximity Radar & Element Inspection Drawer */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            {/* GPS Proximity Card */}
            <div className="bg-[#0A0F1D] border border-blue-900/60 rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  <Compass className="w-4 h-4 text-blue-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-blue-300">
                    GPS Proximity Radar
                  </h3>
                </div>
                {nearestLoading && (
                  <span className="text-[10px] text-blue-400 animate-pulse">Calculating...</span>
                )}
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between items-center text-gray-300">
                  <span className="text-gray-400 text-[11px]">GPS Target:</span>
                  <span className="font-mono text-white text-[11px]">
                    {gpsCoords[0].toFixed(5)}, {gpsCoords[1].toFixed(5)}
                  </span>
                </div>

                {nearestData?.nearest_asset && (
                  <div className="bg-[#111827] p-2 rounded-lg border border-[#1F2937] space-y-1">
                    <span className="text-gray-400 text-[10px] uppercase font-semibold">Closest Electrical Asset</span>
                    <div className="flex items-center justify-between">
                      <strong className="text-sm text-blue-300">{nearestData.nearest_asset.label}</strong>
                      <span className="bg-blue-950 text-blue-300 text-[10px] font-mono px-2 py-0.5 rounded border border-blue-800">
                        {nearestData.nearest_asset.distance_meters} m
                      </span>
                    </div>
                    <div className="flex justify-between text-[11px] text-gray-400">
                      <span>Type: {nearestData.nearest_asset.type}</span>
                      <span>Status: <strong className={nearestData.nearest_asset.status === 'FAULTED' ? 'text-red-400' : 'text-green-400'}>{nearestData.nearest_asset.status}</strong></span>
                    </div>
                  </div>
                )}

                {nearestData?.distance_to_fault_span_km !== null && (
                  <div className="flex justify-between items-center pt-1 border-t border-[#1F2937]">
                    <span className="text-gray-400 text-[11px]">Distance to Fault (F4-S14):</span>
                    <span className="font-mono font-bold text-red-400">
                      {nearestData.distance_to_fault_span_km} km ({Math.round(nearestData.distance_to_fault_span_km * 1000)}m)
                    </span>
                  </div>
                )}

                {nearestData?.distance_to_substation_km !== null && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-[11px]">Distance to Substation:</span>
                    <span className="font-mono text-gray-300">
                      {nearestData.distance_to_substation_km} km
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Top Nearby Assets List */}
            {nearestData?.nearby_assets && nearestData.nearby_assets.length > 0 && (
              <div>
                <span className="text-[11px] uppercase tracking-wider text-gray-400 font-semibold block mb-1.5">
                  Nearby Distribution Assets
                </span>
                <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
                  {nearestData.nearby_assets.slice(0, 4).map((asset) => (
                    <div
                      key={asset.id}
                      onClick={() => {
                        setSelectedNode(asset);
                        setMapCenterTarget([asset.lat, asset.lng]);
                      }}
                      className="bg-[#0A0F1D] hover:bg-[#1A2234] border border-[#1F2937] p-2 rounded-lg cursor-pointer transition text-xs flex items-center justify-between"
                    >
                      <div>
                        <strong className="text-gray-200 block text-[11px]">{asset.id}</strong>
                        <span className="text-[10px] text-gray-400">{asset.type}</span>
                      </div>
                      <div className="text-right">
                        <span className="font-mono text-blue-400 font-semibold block text-[11px]">
                          {asset.distance_meters} m
                        </span>
                        <span className={`text-[9px] font-bold ${asset.status === 'FAULTED' ? 'text-red-400' : 'text-gray-400'}`}>
                          {asset.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Element Inspector */}
            <div>
              <div className="flex items-center space-x-2 pb-2 border-b border-[#1F2937]">
                <Info className="w-3.5 h-3.5 text-blue-400" />
                <h3 className="text-xs font-semibold text-white">Selected Asset Inspector</h3>
              </div>

              {selectedNode ? (
                <div className="mt-2.5 space-y-2 text-xs">
                  <div>
                    <span className="text-gray-400 block text-[10px]">Identifier</span>
                    <strong className="text-sm font-bold text-white font-mono">{selectedNode.id}</strong>
                    <span className="text-[11px] text-gray-400 block">{selectedNode.label}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 bg-[#0A0F1D] p-2 rounded-lg border border-[#1F2937]">
                    <div>
                      <span className="text-gray-400 text-[10px]">Type</span>
                      <strong className="block text-blue-400 text-[11px]">{selectedNode.type}</strong>
                    </div>
                    <div>
                      <span className="text-gray-400 text-[10px]">Status</span>
                      <strong className={`block text-[11px] ${selectedNode.status === 'FAULTED' ? 'text-red-400' : (selectedNode.status === 'ENERGIZED' ? 'text-green-400' : 'text-amber-400')}`}>
                        {selectedNode.status}
                      </strong>
                    </div>
                  </div>

                  <div className="space-y-1 pt-1 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-gray-400">GPS Coordinates:</span>
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
                      <div className="p-1.5 bg-red-950/40 border border-red-800 rounded text-red-300 font-semibold mt-1">
                        Critical Load: {selectedNode.metadata.critical_name}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-gray-500">
                  Click any asset or line span on the map to inspect telemetry.
                </div>
              )}
            </div>
          </div>

          <div className="pt-2 border-t border-[#1F2937] text-[10px] text-gray-400 space-y-1">
            <div className="text-amber-400 font-medium">⚠️ SYNTHETIC DEMO DATA</div>
            <p>GPS coordinates simulate North Bengaluru 11kV distribution feeder corridors.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
