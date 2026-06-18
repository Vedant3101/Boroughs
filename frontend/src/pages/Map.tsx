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
import {
  FilterSidebar,
  EMPTY_FILTERS,
  type BarFilters,
} from "@/components/FilterSidebar";
import styles from "./Map.module.scss";

const NYC_CENTER = { lat: 40.7549, lng: -73.984 }; // Midtown-ish
const DEFAULT_ZOOM = 13;
const MAX_RADIUS_M = 8_000;
const MAX_RESULTS = 200;
const REFETCH_DEBOUNCE_MS = 400;

const MAP_CONTAINER_STYLE = { width: "100%", height: "100%" };

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
  const filtersRef = useRef<BarFilters>(EMPTY_FILTERS);

  const [bars, setBars] = useState<Bar[]>([]);
  const [selected, setSelected] = useState<Bar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<BarFilters>(EMPTY_FILTERS);

  // Keep ref in sync so refetchBars (used in event handlers) sees current filters
  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

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

    const f = filtersRef.current;

    setLoading(true);
    setError(null);
    try {
      const result = await fetchBars({
        lat: center.lat(),
        lng: center.lng(),
        radius,
        page_size: MAX_RESULTS,
        search: f.search || undefined,
        price_max: f.priceMax ?? undefined,
      });
      setBars(result.results);
    } catch (err) {
      console.error("fetchBars failed", err);
      setError("Couldn't load bars for this area.");
    } finally {
      setLoading(false);
    }
  }, []);

  const scheduleRefetch = useCallback(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(refetchBars, REFETCH_DEBOUNCE_MS);
  }, [refetchBars]);

  // Filter changes also trigger refetch (not just map moves)
  useEffect(() => {
    if (!isLoaded || !mapRef.current) return;
    scheduleRefetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, isLoaded]);

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
    <div className={styles.layout}>
      <FilterSidebar
        value={filters}
        onChange={setFilters}
        resultCount={bars.length}
        loading={loading}
      />

      <div className={styles.mapWrapper}>
        {error && <div className={styles.errorBadge}>{error}</div>}

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
          onIdle={scheduleRefetch}
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
    </div>
  );
}
