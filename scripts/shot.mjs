// Dev-only: screenshot the running app in headless Chrome. Usage: node shot.mjs <name> [ask question] [lang]
import { chromium } from 'playwright-core'

const [name = 'home', question, lang = 'en'] = process.argv.slice(2)
const browser = await chromium.launch({ channel: 'chrome' })
const widths = question ? [1440, 390] : [1440, 768, 390]
for (const w of widths) {
  const page = await browser.newPage({ viewport: { width: w, height: w < 500 ? 874 : 900 }, deviceScaleFactor: 1 })
  await page.addInitScript(([lang]) => {
    localStorage.setItem('fasal-kavach.profile.v1', JSON.stringify({ lat: 20.0868, lon: 74.1278, place: 'Niphad, Nashik, Maharashtra', crop: 'onion', sowing_date: '2026-09-15', language: lang }))
  }, [lang])
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message))
  await page.goto('http://localhost:8000/', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  if (question && w === widths[0]) {
    await page.fill('#q', question)
    await page.getByRole('button', { name: process.env.SEND || 'Get advice' }).click()
    await page.waitForSelector('article', { timeout: 120000 })
    await page.waitForTimeout(2500)
  }
  await page.screenshot({ path: `shots/${name}-${w}.png`, fullPage: true })
  console.log('saved', `shots/${name}-${w}.png`)
  await page.close()
  if (question) break
}
await browser.close()
