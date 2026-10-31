import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { ndviMap, searchPlaces, type NdviMap } from '../api'

// MapLibre 6 loads its worker as a separate module; Vite must emit it as an asset.
maplibregl.setWorkerUrl(workerUrl)

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    imagery: {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 19,
      attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
    },
    labels: {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 19,
    },
  },
  layers: [
    { id: 'imagery', type: 'raster', source: 'imagery', paint: { 'raster-saturation': -0.15, 'raster-brightness-max': 0.9 } },
    { id: 'labels', type: 'raster', source: 'labels', paint: { 'raster-opacity': 0.85 } },
  ],
}

const INDIA: [number, number] = [78.9, 22.5]

interface Props {
  autoNdvi?: boolean
  lat: number | null
  lon: number | null
  placeholder: string
  hint: string
  onPick: (lat: number, lon: number) => void
}

export function FieldMap({ lat, lon, placeholder, hint, onPick, autoNdvi }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const marker = useRef<maplibregl.Marker | null>(null)
  const onPickRef = useRef(onPick)
  onPickRef.current = onPick
  const [q, setQ] = useState('')
  const [results, setResults] = useState<{ name: string; lat: number; lon: number }[]>([])
  const [searchError, setSearchError] = useState('')
  const [searching, setSearching] = useState(false)
  const [ndvi, setNdvi] = useState<{ state: 'off' | 'loading' | 'on' | 'error'; data?: NdviMap; error?: string }>({ state: 'off' })
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!el.current || map.current) return
    const m = new maplibregl.Map({
      container: el.current,
      style: STYLE,
      center: lat != null && lon != null ? [lon, lat] : INDIA,
      zoom: lat != null ? 14 : 4,
      attributionControl: { compact: true },
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    const locate = new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true } })
    locate.on('geolocate', (e: any) => onPickRef.current(e.coords.latitude, e.coords.longitude))
    m.addControl(locate, 'bottom-right')
    // The panel's size changes as results stream in; keep the canvas matched to it.
    const ro = new ResizeObserver(() => m.resize())
    ro.observe(el.current)
    m.on('load', () => setReady(true))
    m.on('click', (e: maplibregl.MapMouseEvent) => onPickRef.current(e.lngLat.lat, e.lngLat.lng))
    map.current = m
    return () => {
      ro.disconnect()
      m.remove()
      map.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m || lat == null || lon == null) return
    if (!marker.current) {
      const dot = document.createElement('div')
      dot.className = 'relative h-5 w-5'
      dot.innerHTML =
        '<span class="absolute inset-0 rounded-full bg-[var(--color-accent)]/40" style="animation:pulse-ring 1.8s var(--ease-quart) infinite"></span>' +
        '<span class="absolute inset-[5px] rounded-full bg-[var(--color-accent)] ring-2 ring-[#101010]"></span>'
      const mk = new maplibregl.Marker({ element: dot, draggable: true }).setLngLat([lon, lat]).addTo(m)
      mk.on('dragend', () => {
        const p = mk.getLngLat()
        onPickRef.current(p.lat, p.lng)
      })
      marker.current = mk
    } else {
      marker.current.setLngLat([lon, lat])
    }
    if (m.getZoom() < 12) m.flyTo({ center: [lon, lat], zoom: 15, speed: 1.6 })
  }, [lat, lon])

  // A new pin invalidates the overlay.
  useEffect(() => {
    setNdvi((n) => (n.state === 'off' ? n : { state: 'off' }))
  }, [lat, lon])

  // Auto-show the overlay when the parent says satellite data was just used.
  useEffect(() => {
    if (autoNdvi && ndvi.state === 'off') toggleNdvi()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoNdvi])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    if (m.getLayer('ndvi')) m.removeLayer('ndvi')
    if (m.getSource('ndvi')) m.removeSource('ndvi')
    if (ndvi.state === 'on' && ndvi.data) {
      m.addSource('ndvi', { type: 'image', url: ndvi.data.png, coordinates: ndvi.data.corners as any })
      m.addLayer({ id: 'ndvi', type: 'raster', source: 'ndvi', paint: { 'raster-opacity': 0.85, 'raster-resampling': 'nearest', 'raster-fade-duration': 300 } }, 'labels')
    }
  }, [ndvi, ready])

  async function toggleNdvi() {
    if (lat == null || lon == null) return
    if (ndvi.state === 'on') return setNdvi({ ...ndvi, state: 'off' })
    if (ndvi.data) return setNdvi({ ...ndvi, state: 'on' })
    setNdvi({ state: 'loading' })
    try {
      setNdvi({ state: 'on', data: await ndviMap(lat, lon) })
    } catch (err: any) {
      setNdvi({ state: 'error', error: err.message })
    }
  }

  async function search(e: React.FormEvent) {
    e.preventDefault()
    if (q.trim().length < 2) return
    setSearching(true)
    setSearchError('')
    try {
      const r = await searchPlaces(q)
      setResults(r)
      if (!r.length) setSearchError('No place found in India with that name.')
    } catch (err: any) {
      setSearchError(err.message)
    } finally {
      setSearching(false)
    }
  }

  function choose(r: { lat: number; lon: number }) {
    setResults([])
    map.current?.flyTo({ center: [r.lon, r.lat], zoom: 15, speed: 1.6 })
  }

  return (
    <div className="relative h-full min-h-[320px] w-full overflow-hidden rounded-[16px]">
      <div ref={el} style={{ position: "absolute", inset: 0 }} />
      <form onSubmit={search} className="absolute top-3 left-3 right-3 z-10 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className="h-11 min-w-0 flex-1 rounded-[12px] border border-line-2 bg-[#101010b3] px-4 text-[14px] text-ink placeholder:text-ink-3 backdrop-blur-[20px] outline-none focus:border-ink-3"
        />
        <button type="submit" className="h-11 rounded-[12px] border border-line-2 bg-[#101010b3] px-4 text-[13px] text-ink-2 backdrop-blur-[20px] transition-colors duration-300 hover:text-ink active:scale-[.98]">
          {searching ? '…' : 'Go'}
        </button>
      </form>
      {(results.length > 0 || searchError) && (
        <div className="absolute top-16 left-3 right-3 z-10 overflow-hidden rounded-[12px] border border-line-2 bg-[#101010e6] backdrop-blur-[20px]">
          {searchError && <p className="px-4 py-3 text-[13px] text-ink-3">{searchError}</p>}
          {results.map((r) => (
            <button key={`${r.lat},${r.lon}`} onClick={() => choose(r)} className="block w-full truncate px-4 py-3 text-left text-[13px] text-ink-2 hover:bg-fill-2 hover:text-ink">
              {r.name}
            </button>
          ))}
        </div>
      )}
      {lat != null && (
        <div className="absolute bottom-3 left-3 z-10 flex flex-col items-start gap-2">
          {ndvi.state === 'on' && ndvi.data && (
            <div className="rounded-[12px] border border-line-2 bg-[#101010cc] px-3 py-2 backdrop-blur-[20px]">
              <div className="mb-1.5 h-1.5 w-[148px] rounded-full" style={{ background: 'linear-gradient(90deg,#784828,#b08450,#d6c46a,#96c45a,#4ca046,#186e32)' }} />
              <div className="flex justify-between font-mono text-[10px] text-ink-3">
                <span>bare</span>
                <span>dense crop</span>
              </div>
              <div className="mt-1 font-mono text-[10px] text-ink-3 num">Sentinel-2 · {ndvi.data.date} · 10 m</div>
            </div>
          )}
          {ndvi.state === 'error' && <div className="max-w-[240px] rounded-[10px] bg-[#101010cc] px-3 py-2 text-[11px] text-moderate backdrop-blur-[20px]">{ndvi.error}</div>}
          <button
            onClick={toggleNdvi}
            aria-pressed={ndvi.state === 'on'}
            className={`flex h-9 items-center gap-2 rounded-full border px-3.5 text-[12px] backdrop-blur-[20px] transition-colors duration-300 active:scale-[.98] ${
              ndvi.state === 'on' ? 'border-accent/50 bg-accent/15 text-accent' : 'border-line-2 bg-[#101010b3] text-ink-2 hover:text-ink'
            }`}
          >
            {ndvi.state === 'loading' ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-ink-4 border-t-ink" /> : <span className="h-2 w-2 rounded-full bg-accent" />}
            {ndvi.state === 'loading' ? 'Reading satellite…' : 'Crop vigour (NDVI)'}
          </button>
        </div>
      )}
      {lat == null && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-line-2 bg-[#101010cc] px-4 py-2 text-[13px] text-ink-2 backdrop-blur-[20px]">
          {hint}
        </div>
      )}
    </div>
  )
}
