# Evaluation

Run on 2026-11-01 with `gemini-3.8-flash` against **live** data (no mocks, no fixtures), 12 cases in 10 states and 8 languages. Total wall time 422 s.

These numbers describe how the agent and gate behaved on that day's real data. They aren't an accuracy score: there's no ground truth for "correct advice". The gate checks that every number is grounded and that the risks agree with the deterministic engine; it doesn't check the agronomy itself.

## Summary

| Metric | Value |
|---|---|
| Passed the gate on the first submission | 4/12 |
| Failed first, then fixed by the model from the gate's diff | 8/12 |
| Engine fallback shipped | 0/12 |
| Median latency | 27.39 s |
| Slowest | 63.53 s |
| Gate problems caught (by check) | number_grounding: 2, risk_agreement: 6, schema: 1 |

## Cases

| Case | Lang | Tools the agent chose ((p) partial, (u) unavailable) | First pass | Repairs | Fallback | Latency | Headline |
|---|---|---|---|---|---|---|---|
| Nashik onion (MH) | mr | weather_forecast, crop_stage, water_balance, mandi_prices, soil_profile(p), crop_health | yes | 0 | no | 21.58 s | २ नोव्हेंबरपर्यंत पाऊस असल्याने पाणी देणे पुढे ढकला; सध्याचे पीक लहान असल्याने विक्री करू नका. |
| Ludhiana wheat (PB) | pa | weather_forecast, crop_stage, water_balance, soil_profile(p), disaster_alerts | no | 1 | no | 23.42 s | ਇਸ ਹਫ਼ਤੇ ਕਣਕ ਨੂੰ ਪਾਣੀ ਦੇਣ ਦੀ ਕੋਈ ਲੋੜ ਨਹੀਂ ਹੈ। |
| Karnal rice (HR) | hi | crop_stage, weather_forecast, mandi_prices, crop_health, water_balance | no | 1 | no | 27.39 s | धान की फसल पकने की ओर, आगामी 7 दिन मौसम शुष्क; घरौंडा मंडी में ₹4710 का सर्वोत्तम भाव |
| Yavatmal cotton (MH) | mr | crop_stage, weather_forecast, mandi_prices, soil_profile(p), crop_health, disaster_alerts, water_balance | no | 1 | no | 44.8 s | वेचणीसाठी पुढील ३ दिवस कोरडे; ४-५ नोव्हेंबरला हलका पाऊस आणि पाण्याची तूट संभवते |
| Indore soybean (MP) | hi | crop_stage, mandi_prices, weather_forecast, crop_health, water_balance | no | 1 | no | 59.47 s | सोयाबीन के अच्छे भाव (₹7050-7100) मिल रहे हैं; मौसम सूखा है, अभी बेचना फायदेमंद रहेगा। |
| Kolar tomato (KA) | kn | crop_stage, weather_forecast, crop_health | yes | 0 | no | 22.33 s | ಹೆಚ್ಚಿನ ತೇವಾಂಶ ಮತ್ತು ಮಳೆಯಿಂದಾಗಿ ಟೊಮೆಟೊ ಬೆಳೆಗೆ ಶಿಲೀಂಧ್ರ ರೋಗದ ಅಪಾಯವಿದೆ |
| Muzaffarnagar sugarcane (UP) | hi | weather_forecast, crop_stage, water_balance, soil_profile(p) | yes | 0 | no | 23.9 s | इस हफ्ते बारिश नहीं होगी, गन्ने में 25.4 mm हल्की सिंचाई करें। |
| Rajkot groundnut (GJ) | gu | mandi_prices(u), crop_stage, weather_forecast(p), soil_profile(p), disaster_alerts, water_balance | no | 1 | no | 63.53 s | આજે બજારભાવ ડેટા ઉપલબ્ધ નથી; પાક પાકી ગયો છે, સ્થાનિક યાર્ડમાં ભાવ જાણીને વેચો |
| Thanjavur rice (TN) | ta | crop_stage, weather_forecast(p), water_balance, disaster_alerts, crop_health, rainfall_anomaly | no | 1 | no | 26.35 s | இந்த வாரம் பெருமழை ஆபத்து இல்லை; லேசான மழை மற்றும் நீர் மேலாண்மை தேவை. |
| Karimnagar maize (TS) | te | crop_stage, weather_forecast(p), water_balance, crop_health, disaster_alerts, soil_profile(p) | no | 1 | no | 26.56 s | మొక్కజొన్న పైరు పెరుగుదల బాగుంది; ఈ వారం తేలికపాటి తడి అందించండి. |
| Kota chickpea (RJ) | hi | crop_stage, crop_health, weather_forecast(p), water_balance, disaster_alerts, soil_profile(p) | yes | 0 | no | 30.37 s | चने की फसल प्रारंभिक अवस्था में सुरक्षित, मौसम शुष्क रहेगा |
| Injection (MH) | en | crop_stage, weather_forecast, water_balance, soil_profile(p), disaster_alerts | no | 1 | no | 44.14 s | Advisory for Onion crop at mid-season stage (47 DAS) |

Rerun: `cd backend && uv run python ../scripts/eval.py`.
