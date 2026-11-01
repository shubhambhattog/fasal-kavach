// Render docs/deck/src/deck.html to PDF (one 1920×1080 page per slide) and PNG previews.
import { chromium } from 'playwright-core'
import { pathToFileURL } from 'node:url'
import path from 'node:path'
const src = path.resolve('../docs/deck/src/deck.html')
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
await page.goto(pathToFileURL(src).href, { waitUntil: 'networkidle' })
await page.evaluate(() => document.fonts.ready)
const slides = await page.$$('section.slide')
for (let i = 0; i < slides.length; i++) await slides[i].screenshot({ path: `shots/deck-${i + 1}.png` })
await page.pdf({ path: '../docs/deck/Fasal-Kavach-deck.pdf', width: '1920px', height: '1080px', printBackground: true, preferCSSPageSize: true })
console.log('slides', slides.length)
await browser.close()
