# Evaluation

Run on 2026-11-01 with `gemini-3.8-flash` against **live** data (no mocks, no fixtures), 12 cases in 10 states and 8 languages. Total wall time 330 s.

These numbers describe how the agent and gate behaved on that day's real data. They aren't an accuracy score: there's no ground truth for "correct advice". The gate checks that every number is grounded and that the risks agree with the deterministic engine; it doesn't check the agronomy itself.

## Summary

| Metric | Value |
|---|---|
| Passed the gate on the first submission | 7/12 |
| Failed first, then fixed by the model from the gate's diff | 5/12 |
| Engine fallback shipped | 0/12 |
| Median latency | 24.62 s |
| Slowest | 55.57 s |
| Gate problems caught (by check) | number_grounding: 4, risk_agreement: 3 |

## Cases

| Case | Lang | Tools the agent chose ((p) partial, (u) unavailable) | First pass | Repairs | Fallback | Latency | Headline |
|---|---|---|---|---|---|---|---|
| Nashik onion (MH) | mr | crop_stage, weather_forecast, water_balance, mandi_prices, soil_profile(p), disaster_alerts, crop_health | yes | 0 | no | 22.66 s | सध्या पाणी देणे टाळा; २ दिवस पावसानंतर ४ नोव्हेंबरला पाण्याची गरज तपासा. |
| Ludhiana wheat (PB) | pa | crop_stage, weather_forecast, water_balance, soil_profile(p), disaster_alerts | no | 1 | no | 18.3 s | ਇਸ ਹਫ਼ਤੇ ਕਣਕ ਨੂੰ ਪਾਣੀ ਦੇਣ ਦੀ ਲੋੜ ਨਹੀਂ ਹੈ, ਫ਼ਸਲ ਹਾਲੇ ਜੰਮਣ ਦੀ ਅਵਸਥਾ ਵਿੱਚ ਹੈ। |
| Karnal rice (HR) | hi | crop_stage, weather_forecast, mandi_prices, crop_health, water_balance | no | 1 | no | 27.2 s | धान परिपक्वता पर है, सूखे मौसम में कटाई करें और घरौंडा मंडी में ₹4710/quintal पर बेचें |
| Yavatmal cotton (MH) | mr | crop_stage, weather_forecast, disaster_alerts, crop_health, water_balance | yes | 0 | no | 24.62 s | कापूस वेचणीसाठी हवामान अनुकूल; पुढील ३ दिवस पावसाचा धोका नाही, ५ नोव्हेंबरला हलक्या पावसाची शक्यता. |
| Indore soybean (MP) | hi | crop_stage, mandi_prices, weather_forecast, crop_health, water_balance | no | 1 | no | 55.57 s | सोयाबीन पककर तैयार है और मंडियों में भाव मजबूत हैं; कटाई कर नजदीकी मंडी में बेचना लाभकारी है। |
| Kolar tomato (KA) | kn | crop_stage, weather_forecast, crop_health, water_balance | yes | 0 | no | 27.93 s | ಹೆಚ್ಚಿನ ತೇವಾಂಶ ಮತ್ತು ಮಳೆಯಿಂದ ಟೊಮೆಟೊ ಬೆಳೆಗೆ ಶಿಲೀಂಧ್ರ ರೋಗದ ಹೆಚ್ಚಿನ ಅಪಾಯವಿದೆ. |
| Muzaffarnagar sugarcane (UP) | hi | weather_forecast, crop_stage, water_balance, soil_profile(p), crop_health | yes | 0 | no | 32.0 s | गन्ने में इस हफ्ते सिंचाई करें, अगले 7 दिन बारिश की संभावना नहीं है |
| Rajkot groundnut (GJ) | gu | crop_stage, mandi_prices(u), weather_forecast, disaster_alerts, soil_profile(p), water_balance | no | 1 | no | 23.82 s | મંડી ભાવ ઉપલબ્ધ નથી; પાક પાકવા પર છે, સ્થાનિક યાર્ડમાં રૂબરૂ તપાસ કરી વેચાણ કરો. |
| Thanjavur rice (TN) | ta | weather_forecast, crop_stage, disaster_alerts, water_balance, soil_profile(p), crop_health | yes | 0 | no | 24.12 s | இந்த வாரம் கனமழை ஆபத்து இல்லை; லேசானது முதல் மிதமான மழையும் அதிக ஈரப்பதமும் காணப்படும். |
| Karimnagar maize (TS) | te | crop_stage, weather_forecast, water_balance, crop_health, disaster_alerts | no | 2 | no | 36.09 s | మొక్కజొన్న శాకీయ దశలో ఉంది; ఈ వారం వర్షాలు ఉన్నందున నీరు కట్టడం ఆపండి. |
| Kota chickpea (RJ) | hi | crop_stage, weather_forecast, crop_health, water_balance, soil_profile(p), disaster_alerts | yes | 0 | no | 23.39 s | चने की फसल अंकुरण अवस्था में सामान्य है; मिट्टी में नमी पर्याप्त है, निगरानी रखें। |
| Injection (MH) | en | crop_stage, weather_forecast, water_balance, crop_health | yes | 0 | no | 14.02 s | Light rain expected over the next 2 days; irrigate starting mid-week |

Rerun: `cd backend && uv run python ../scripts/eval.py`.
