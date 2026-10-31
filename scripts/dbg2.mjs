import { chromium } from 'playwright-core'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let tiles = 0
page.on('response', (r) => { if (r.url().includes('arcgisonline')) tiles++ })
page.on('console', (m) => m.type() === 'error' && console.log('console', m.text().slice(0, 200)))
await page.addInitScript(() => localStorage.setItem('fasal-kavach.profile.v1', JSON.stringify({ lat: 20.0868, lon: 74.1278, place: 'x', crop: 'onion', sowing_date: '2026-09-15', language: 'en' })))
await page.goto('http://localhost:8000/', { waitUntil: 'networkidle' })
await page.waitForTimeout(5000)
console.log('tiles', tiles)
console.log(await page.evaluate(() => { const c = document.querySelector('.maplibregl-canvas'); const p = c?.parentElement?.parentElement; return { canvas: c && [c.clientWidth, c.clientHeight], container: p && [p.clientWidth, p.clientHeight], cls: p?.className } }))
await browser.close()
