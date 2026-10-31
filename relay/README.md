# data.gov.in relay

A single Vercel function in the Mumbai region (`bom1`). data.gov.in refuses connections from
foreign datacenters, so the deployed app (Render, Singapore) fetches mandi prices through it. It
forwards only the allow-listed mandi dataset and requires the `x-relay-token` header.

```bash
vercel deploy --prod --env RELAY_TOKEN=<secret>
```

The app uses it when `DATA_GOV_RELAY_URL` and `DATA_GOV_RELAY_TOKEN` are set, and falls back to calling
data.gov.in directly.
