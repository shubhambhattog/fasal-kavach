// Indian-egress relay for the data.gov.in mandi price API.
// data.gov.in refuses connections from foreign datacenters (seen from Render Singapore), so the
// app's server calls this function, which runs in Vercel's Mumbai region (bom1) and forwards the
// request. It only forwards the one allow-listed dataset, and only with the shared secret.

const ALLOWED = new Set(['9ef84268-d588-465a-a308-a864a43d0070']) // daily mandi prices (Agmarknet)
const UPSTREAM = 'https://api.data.gov.in/resource/'

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' })
  if (!process.env.RELAY_TOKEN || req.headers['x-relay-token'] !== process.env.RELAY_TOKEN) {
    return res.status(401).json({ error: 'unauthorised' })
  }
  const { resource, ...query } = req.query
  if (!ALLOWED.has(resource)) return res.status(400).json({ error: 'resource not allowed' })
  const url = UPSTREAM + resource + '?' + new URLSearchParams(query).toString()
  try {
    const upstream = await fetch(url, { signal: AbortSignal.timeout(10000), headers: { 'User-Agent': 'FasalKavach-relay/0.1' } })
    const body = await upstream.text()
    res.setHeader('Content-Type', upstream.headers.get('content-type') || 'application/json')
    res.setHeader('X-Relay-Region', process.env.VERCEL_REGION || 'unknown')
    return res.status(upstream.status).send(body)
  } catch (err) {
    return res.status(502).json({ error: `upstream failed: ${err.name}` })
  }
}
