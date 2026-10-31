/** UI chrome strings. Advisory text itself comes from the model in the chosen language. */
const en = {
  tagline: 'Advice for your field, from live satellite, weather and mandi data.',
  field: 'Your field',
  searchPlaceholder: 'Search village or town',
  dropPin: 'Tap the map to drop a pin on your field',
  crop: 'Crop',
  sown: 'Sowing date',
  language: 'Language',
  ask: 'Ask about your field',
  askPlaceholder: 'e.g. Should I irrigate this week? Where should I sell?',
  send: 'Get advice',
  stop: 'Stop',
  listening: 'Listening… tap to stop',
  transcribing: 'Writing down what you said…',
  agent: 'What the agent is doing',
  advisory: 'Advice',
  speak: 'Listen',
  sources: 'Sources',
  gaps: 'Missing data',
  forecast: '16-day forecast',
  ndvi: 'Crop vigour from satellite (NDVI)',
  mandi: "Today's mandi prices",
  risks: 'Risks found',
  confidence: 'Confidence',
  when: { today: 'Today', next_3_days: 'Next 3 days', this_week: 'This week', before_harvest: 'Before harvest' },
  level: { low: 'Low', moderate: 'Moderate', high: 'High' },
  examples: ['What should I do on my field this week?', 'Should I irrigate or spray in the next 3 days?', 'Is my crop healthy? Where should I sell?'],
}

type Strings = typeof en

const hi: Strings = {
  ...en,
  tagline: 'आपके खेत के लिए सलाह — लाइव सैटेलाइट, मौसम और मंडी डेटा से।',
  field: 'आपका खेत',
  searchPlaceholder: 'गाँव या शहर खोजें',
  dropPin: 'नक्शे पर अपने खेत पर टैप करें',
  crop: 'फसल',
  sown: 'बुवाई की तारीख',
  language: 'भाषा',
  ask: 'अपने खेत के बारे में पूछें',
  askPlaceholder: 'जैसे: इस हफ्ते सिंचाई करूँ? फसल कहाँ बेचूँ?',
  send: 'सलाह लें',
  stop: 'रोकें',
  listening: 'सुन रहे हैं… रोकने के लिए टैप करें',
  transcribing: 'आपकी बात लिख रहे हैं…',
  agent: 'एजेंट क्या कर रहा है',
  advisory: 'सलाह',
  speak: 'सुनें',
  sources: 'स्रोत',
  gaps: 'अनुपलब्ध डेटा',
  forecast: '16 दिन का मौसम',
  ndvi: 'सैटेलाइट से फसल की हरियाली (NDVI)',
  mandi: 'आज के मंडी भाव',
  risks: 'जोखिम',
  confidence: 'भरोसा',
  when: { today: 'आज', next_3_days: 'अगले 3 दिन', this_week: 'इस हफ्ते', before_harvest: 'कटाई से पहले' },
  level: { low: 'कम', moderate: 'मध्यम', high: 'ज़्यादा' },
  examples: ['इस हफ्ते खेत में क्या करूँ?', 'अगले 3 दिन सिंचाई या छिड़काव करूँ?', 'फसल ठीक है? कहाँ बेचूँ?'],
}

const mr: Strings = {
  ...en,
  tagline: 'तुमच्या शेतासाठी सल्ला — थेट उपग्रह, हवामान आणि बाजारभाव माहितीवरून.',
  field: 'तुमचे शेत',
  searchPlaceholder: 'गाव किंवा शहर शोधा',
  dropPin: 'नकाशावर तुमच्या शेतावर टॅप करा',
  crop: 'पीक',
  sown: 'पेरणीची तारीख',
  language: 'भाषा',
  ask: 'तुमच्या शेताबद्दल विचारा',
  askPlaceholder: 'उदा. या आठवड्यात पाणी द्यावे का? कांदा कुठे विकावा?',
  send: 'सल्ला घ्या',
  stop: 'थांबवा',
  listening: 'ऐकत आहोत… थांबवण्यासाठी टॅप करा',
  transcribing: 'तुमचे बोलणे लिहित आहोत…',
  agent: 'एजंट काय करत आहे',
  advisory: 'सल्ला',
  speak: 'ऐका',
  sources: 'स्रोत',
  gaps: 'उपलब्ध नसलेली माहिती',
  forecast: '16 दिवसांचा हवामान अंदाज',
  ndvi: 'उपग्रहावरून पिकाची हिरवळ (NDVI)',
  mandi: 'आजचे बाजारभाव',
  risks: 'धोके',
  confidence: 'खात्री',
  when: { today: 'आज', next_3_days: 'पुढील 3 दिवस', this_week: 'या आठवड्यात', before_harvest: 'काढणीपूर्वी' },
  level: { low: 'कमी', moderate: 'मध्यम', high: 'जास्त' },
  examples: ['या आठवड्यात शेतात काय करावे?', 'पुढील 3 दिवसांत पाणी द्यावे की फवारणी करावी?', 'पीक निरोगी आहे का? कुठे विकावे?'],
}

const TABLE: Record<string, Strings> = { en, hi, mr }

export const LANGUAGES: Record<string, string> = {
  en: 'English',
  hi: 'हिन्दी',
  mr: 'मराठी',
  gu: 'ગુજરાતી',
  pa: 'ਪੰਜਾਬੀ',
  bn: 'বাংলা',
  ta: 'தமிழ்',
  te: 'తెలుగు',
  kn: 'ಕನ್ನಡ',
}

export const SPEECH_LANG: Record<string, string> = {
  en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', gu: 'gu-IN', pa: 'pa-IN', bn: 'bn-IN', ta: 'ta-IN', te: 'te-IN', kn: 'kn-IN',
}

export function t(lang: string): Strings {
  return TABLE[lang] ?? en
}

export const TOOL_LABELS: Record<string, string> = {
  get_weather_forecast: 'Weather forecast',
  get_rainfall_anomaly: 'Rainfall vs 20-year normal',
  get_crop_health: 'Sentinel-2 crop vigour',
  get_soil_profile: 'Soil profile',
  get_mandi_prices: 'Mandi prices',
  get_disaster_alerts: 'Disaster alerts',
  get_crop_stage: 'Crop growth stage',
  get_water_balance: 'Crop water balance',
}

export const RISK_LABELS: Record<string, string> = {
  heat_stress: 'Heat stress',
  water_deficit: 'Water need',
  heavy_rain: 'Heavy rain',
  disease_weather: 'Disease weather',
  vegetation_decline: 'Crop vigour',
  rain_deficit: 'Rain vs normal',
  disaster: 'Disaster alert',
  market: 'Market',
}
