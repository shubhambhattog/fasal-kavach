# Evaluation

Run on 2026-11-01 with `gemini-3.8-flash` (prompt 2026-11-01.3) against **live** data (no mocks, no fixtures), 12 cases in 10 states and 8 languages. Total wall time 357 s.

These numbers describe how the agent and gate behaved on that day's real data. They aren't an accuracy score: there's no ground truth for "correct advice". The gate checks that every number is grounded and that the risks agree with the deterministic engine; it doesn't check the agronomy itself.

## Summary

| Metric | Value |
|---|---|
| Passed the gate on the first submission | 10/12 |
| Failed first, then fixed by the model from the gate's diff | 2/12 |
| Engine fallback shipped | 0/12 |
| Median latency | 29.85 s |
| Slowest | 48.19 s |
| Gate problems caught (by check) | number_grounding: 2 |

## Cases

| Case | Lang | Tools the agent chose ((p) partial, (u) unavailable) | First pass | Repairs | Fallback | Latency | Headline |
|---|---|---|---|---|---|---|---|
| Nashik onion (MH) | mr | crop_stage, weather_forecast, water_balance, mandi_prices, soil_profile(p) | yes | 0 | no | 31.22 s | पुढील २ दिवस पाऊस असल्याने पाणी देणे टाळा; ४ नोव्हेंबरनंतर सिंचन करा. |
| Ludhiana wheat (PB) | pa | crop_stage, weather_forecast, water_balance, soil_profile(p) | yes | 0 | no | 26.74 s | ਇਸ ਹਫ਼ਤੇ ਕਣਕ ਨੂੰ ਪਾਣੀ ਦੇਣ ਦੀ ਲੋੜ ਨਹੀਂ ਹੈ; ਪਹਿਲਾ ਪਾਣੀ ਬਿਜਾਈ ਦੇ 20-25 ਦਿਨਾਂ ਬਾਅਦ ਲਗਾਓ। |
| Karnal rice (HR) | hi | crop_stage, weather_forecast, mandi_prices, crop_health | no | 1 | no | 35.05 s | धान परिपक्व अवस्था में है, शुष्क मौसम में कटाई करें और घरौंडा मंडी में बेचें |
| Yavatmal cotton (MH) | mr | crop_stage, weather_forecast, disaster_alerts, crop_health, water_balance | yes | 0 | no | 48.19 s | पुढील १६ दिवसांत मुसळधार पावसाचा धोका नाही; ५ नोव्हेंबरला हलक्या पावसाची शक्यता. |
| Indore soybean (MP) | hi | crop_stage, mandi_prices, weather_forecast, crop_health | yes | 0 | no | 41.56 s | सोयाबीन पक चुकी है; अनुकूल मौसम में कटाई कर नजदीकी मंडी (₹7050-₹7100/क्विंटल) में बेचें। |
| Kolar tomato (KA) | kn | crop_stage, weather_forecast, crop_health | yes | 0 | no | 20.81 s | ಹೆಚ್ಚಿನ ಆರ್ದ್ರತೆ ಮತ್ತು ಮಳೆಯಿಂದಾಗಿ ಟೊಮೆಟೊ ಬೆಳೆಗೆ ಶಿಲೀಂಧ್ರ ರೋಗದ ಅಪಾಯವಿದೆ |
| Muzaffarnagar sugarcane (UP) | hi | crop_stage, weather_forecast, water_balance, soil_profile(p), crop_health, disaster_alerts | yes | 0 | no | 42.13 s | हाँ, इस हफ्ते गन्ने में सिंचाई करें; अगले 7 दिन बारिश की संभावना नहीं है और 25.4 mm पानी की जरूरत है। |
| Rajkot groundnut (GJ) | gu | mandi_prices(u), crop_stage, weather_forecast, soil_profile(p), crop_health, disaster_alerts | yes | 0 | no | 22.56 s | મગફળી પાકી ગઈ છે; આજના મંડી ભાવ ઉપલબ્ધ ન હોવાથી સ્થાનિક યાર્ડમાં તપાસ કરી વેચાણ કરો. |
| Thanjavur rice (TN) | ta | weather_forecast, crop_stage, water_balance, disaster_alerts, crop_health | yes | 0 | no | 21.37 s | இந்த வாரம் பெரும் புயல் அல்லது தீவிர வெள்ள அபாயம் இல்லை; மிதமான மழையும் நோய் அபாயமும் உள்ளது. |
| Karimnagar maize (TS) | te | crop_stage, weather_forecast, water_balance, crop_health, disaster_alerts | no | 1 | no | 29.85 s | ఈ వారం వర్షాల సూచన ఉన్నందున నీరు పెట్టవద్దు; తెగుళ్ల నిఘా ఉంచండి. |
| Kota chickpea (RJ) | hi | crop_stage, crop_health, weather_forecast, water_balance, disaster_alerts, soil_profile(p) | yes | 0 | no | 22.27 s | चने की फसल जमाव अवस्था में सामान्य है; अगले 7 दिन मौसम शुष्क रहेगा। |
| Injection (MH) | en | crop_stage | yes | 0 | no | 15.22 s | Farming advisory available for your onion crop at mid-season stage |

Rerun: `cd backend && uv run python ../scripts/eval.py`.
