import {
  GoogleMap,
  InfoWindow,
  Marker,
  useJsApiLoader,
} from "@react-google-maps/api";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchBars, type Bar } from "@/api/bars";
import { haversineMeters } from "@/lib/geo";
import { BarInfoCard } from "@/components/BarInfoCard";
import styles from "./Map.module.scss";

const NYC_CENTER = { lat: 40.7549, lng: -73.984 }; // Midtown-ish
const DEFAULT_ZOOM = 13;
const MAX_RADIUS_M = 8_000; // cap to keep response sizes sane
const MAX_RESULTS = 200;
const REFETCH_DEBOUNCE_MS = 400;

const MAP_CONTAINER_STYLE = { width: "100%", height: "100%" };

// Slight dark-mode tweaks so the map matches the app palette
const MAP_OPTIONS: google.maps.MapOptions = {
  disableDefaultUI: false,
  streetViewControl: false,
  mapTypeControl: false,
  fullscreenControl: false,
  clickableIcons: false,
};

export default function MapPage() {
  const { isLoaded, loadError } = useJsApiLoader({
    id: "boroughs-google-map",
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
  });

  const mapRef = useRef<google.maps.Map | null>(null);
  const debounceRef = useRef<number | null>(null);

  const [bars, setBars] = useState<Bar[]>([]);
  const [selected, setSelected] = useState<Bar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetchBars = useCallback(async () => {
    const map = mapRef.current;
    if (!map) return;

    const center = map.getCenter();
    const bounds = map.getBounds();
    if (!center || !bounds) return;

    const ne = bounds.getNorthEast();
    const radius = Math.min(
      haversineMeters(center.lat(), center.lng(), ne.lat(), ne.lng()),
      MAX_RADIUS_M,
    );

    setLoading(true);
    setError(null);
    try {
      const result = await fetchBars({
        lat: center.lat(),
        lng: center.lng(),
        radius,
        page_size: MAX_RESULTS,
      });
      setBars(result.results);
    } catch (err) {
      console.error("fetchBars failed", err);
      setError("Couldn't load bars for this area.");
    } finally {
      setLoading(false);
    }
  }, []);

  const onIdle = useCallback(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(refetchBars, REFETCH_DEBOUNCE_MS);
  }, [refetchBars]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, []);

  if (loadError) {
    return (
      <div className={styles.message}>
        Failed to load Google Maps. Check that the Maps JavaScript API is enabled
        and your key is valid.
      </div>
    );
  }
  if (!isLoaded) {
    return <div className={styles.message}>Loading map…</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.statusBar}>
        {loading ? (
          <span>Loading bars…</span>
        ) : error ? (
          <span className={styles.error}>{error}</span>
        ) : (
          <span>
            {bars.length} bar{bars.length === 1 ? "" : "s"} in view
          </span>
        )}
      </div>

      <GoogleMap
        mapContainerStyle={MAP_CONTAINER_STYLE}
        center={NYC_CENTER}
        zoom={DEFAULT_ZOOM}
        options={MAP_OPTIONS}
        onLoad={(map) => {
          mapRef.current = map;
        }}
        onUnmount={() => {
          mapRef.current = null;
        }}
        onIdle={onIdle}
        onClick={() => setSelected(null)}
      >
        {bars.map((bar) => (
          <Marker
            key={bar.id}
            position={{
              lat: parseFloat(bar.latitude),
              lng: parseFloat(bar.longitude),
            }}
            title={bar.name}
            onClick={() => setSelected(bar)}
          />
        ))}

        {selected && (
          <InfoWindow
            position={{
              lat: parseFloat(selected.latitude),
              lng: parseFloat(selected.longitude),
            }}
            onCloseClick={() => setSelected(null)}
            options={{ pixelOffset: new google.maps.Size(0, -34) }}
          >
            <BarInfoCard bar={selected} />
          </InfoWindow>
        )}
      </GoogleMap>
    </div>
  );
}
