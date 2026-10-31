// Dev-only: drive the mic button with Chrome's fake audio device playing a WAV file.
import { chromium } from 'playwright-core'
const browser = await chromium.launch({ channel: 'chrome', args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-audio-capture=/tmp/fk-tts.wav'] })
const ctx = await browser.newContext({ permissions: ['microphone'], viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message))
await page.addInitScript(() => localStorage.setItem('fasal-kavach.profile.v1', JSON.stringify({ lat: 20.0868, lon: 74.1278, place: 'Niphad', crop: 'onion', sowing_date: '2026-09-15', language: 'mr' })))
await page.goto('http://localhost:8000/', { waitUntil: 'networkidle' })
await page.getByRole('button', { name: 'Speak your question' }).click()
await page.waitForTimeout(7000)
await page.locator('#q + button').click()
await page.waitForTimeout(12000); console.log('mic error:', await page.locator('p.text-moderate').allTextContents())
console.log('TRANSCRIPT:', await page.inputValue('#q'))
await browser.close()
