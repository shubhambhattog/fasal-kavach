import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { searchPlaces } from '../api'

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
  lat: number | null
  lon: number | null
  placeholder: string
  hint: string
  onPick: (lat: number, lon: number) => void
}

export function FieldMap({ lat, lon, placeholder, hint, onPick }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const marker = useRef<maplibregl.Marker | null>(null)
  const onPickRef = useRef(onPick)
  onPickRef.current = onPick
  const [q, setQ] = useState('')
  const [results, setResults] = useState<{ name: string; lat: number; lon: number }[]>([])
  const [searchError, setSearchError] = useState('')
  const [searching, setSearching] = useState(false)

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
      {lat == null && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-line-2 bg-[#101010cc] px-4 py-2 text-[13px] text-ink-2 backdrop-blur-[20px]">
          {hint}
        </div>
      )}
    </div>
  )
}
