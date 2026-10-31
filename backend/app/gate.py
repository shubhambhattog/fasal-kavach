"""The gate: checks a submitted advisory against the evidence and the risk engine.

On failure it returns a diff (what's wrong and where), never the engine's answer. The model then
fixes its own advisory. Checks: schema, citations, number grounding, risk agreement, data-gap
disclosure, dosage safety and language script.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from .engine import LEVELS, Signal
from .evidence import EvidenceStore

ENFORCED_RISKS = {"heat_stress", "water_deficit", "heavy_rain", "disease_weather", "vegetation_decline", "rain_deficit", "disaster"}
WHEN = {"today", "next_3_days", "this_week", "before_harvest"}

SCRIPTS = {  # language → (Unicode block start, end)
    "hi": (0x0900, 0x097F), "mr": (0x0900, 0x097F), "bn": (0x0980, 0x09FF), "pa": (0x0A00, 0x0A7F),
    "gu": (0x0A80, 0x0AFF), "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF),
}

NUM_RE = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")
MONTHS = (
    "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|"
    "जनवरी|फ़रवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|सितम्बर|अक्टूबर|अक्तूबर|नवंबर|नवम्बर|दिसंबर|दिसम्बर|"
    "जानेवारी|फेब्रुवारी|एप्रिल|मे|जुलै|ऑगस्ट|सप्टेंबर|ऑक्टोबर|नोव्हेंबर|डिसेंबर|"
    # Telugu, Tamil, Kannada, Gujarati, Punjabi, Bengali (found missing in eval v2: a Telugu "6 Nov" failed twice)
    "జనవరి|ఫిబ్రవరి|మార్చి|ఏప్రిల్|మే|జూన్|జూలై|ఆగస్టు|సెప్టెంబర్|అక్టోబర్|నవంబర్|డిసెంబర్|"
    "ஜனவரி|பிப்ரவரி|மார்ச்|ஏப்ரல்|மே|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்|"
    "ಜನವರಿ|ಫೆಬ್ರವರಿ|ಮಾರ್ಚ್|ಏಪ್ರಿಲ್|ಮೇ|ಜೂನ್|ಜುಲೈ|ಆಗಸ್ಟ್|ಸೆಪ್ಟೆಂಬರ್|ಅಕ್ಟೋಬರ್|ನವೆಂಬರ್|ಡಿಸೆಂಬರ್|"
    "જાન્યુઆરી|ફેબ્રુઆરી|માર્ચ|એપ્રિલ|મે|જૂન|જુલાઈ|ઓગસ્ટ|સપ્ટેમ્બર|ઑક્ટોબર|ઓક્ટોબર|નવેમ્બર|ડિસેમ્બર|"
    "ਜਨਵਰੀ|ਫਰਵਰੀ|ਮਾਰਚ|ਅਪ੍ਰੈਲ|ਮਈ|ਜੂਨ|ਜੁਲਾਈ|ਅਗਸਤ|ਸਤੰਬਰ|ਅਕਤੂਬਰ|ਨਵੰਬਰ|ਦਸੰਬਰ|"
    "জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর"
)
DAY_WORDS = "days?|दिन|दिनों|दिवस|दिवसांत|दिवसात|दिवसांनी|दिवसांचा|दिवसांच्या|రోజు|రోజులు|రోజుల|நாள்|நாட்கள்|நாட்களில்|ದಿನ|ದಿನಗಳ|ದಿನಗಳು|દિવસ|દિવસો|ਦਿਨ|ਦਿਨਾਂ|দিন|দিনের"
# Dates and day counts aren't measurements, so they are removed before the grounding check.
DATE_RE = re.compile(
    rf"\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}|\d{{1,2}}\s*(?:{MONTHS})|(?:{MONTHS})\.?\s*\d{{1,2}}(?!\d)|"
    rf"\d{{1,2}}\s*(?:-|–|to|ते|से)?\s*\d{{0,2}}\s*(?:{DAY_WORDS})|20[2-3]\d",
    re.IGNORECASE,
)
DOSE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ml|मिली|मि\.ली|g|gm|ग्राम|kg|किलो|किग्रा|l|litre|liter|लीटर|लिटर)\s*(?:/|per|प्रति|प्रती)\s*"
    r"(?:l|litre|liter|लीटर|लिटर|acre|एकड़|एकर|ha|hectare|हेक्टेयर|हेक्टर|pump|पंप)",
    re.IGNORECASE,
)


@dataclass
class GateResult:
    ok: bool
    problems: list[dict] = field(default_factory=list)

    def add(self, check: str, detail: str) -> None:
        self.ok = False
        self.problems.append({"check": check, "detail": detail})


def ascii_digits(text: str) -> str:
    """Convert Devanagari and other Indic digits to ASCII so numbers can be checked in any script."""
    return "".join(str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch for ch in text)


def extract_numbers(text: str) -> list[float]:
    text = DATE_RE.sub(" ", ascii_digits(text))
    return [float(m.group().replace(",", "")) for m in NUM_RE.finditer(text)]


def allowed_numbers(ev: EvidenceStore, signals: list[Signal], extra_text: str) -> list[tuple[str, float]]:
    nums = list(ev.numbers())
    for s in signals:
        nums += [(f"engine.{s.type}.{k}", float(v)) for k, v in s.numbers.items()]
    for r in ev.results:
        for note in r.notes:
            nums += [(f"note:{r.tool}", v) for v in extract_numbers(note)]
    nums += [("question", v) for v in extract_numbers(extra_text)]
    return nums


def grounded(x: float, allowed: list[tuple[str, float]]) -> bool:
    if x <= 3 and x == int(x):  # "2-3 waterings", "1 acre"
        return True
    for _, v in allowed:
        v = abs(v)
        if abs(x - v) <= (0.5 if v < 10 else max(0.02 * v, 0.5)):
            return True
    return False


def nearest(x: float, allowed: list[tuple[str, float]]) -> str:
    candidates = [(fid, v) for fid, v in allowed if fid != "question" and not fid.startswith("note:")]
    if not candidates:
        return "no numeric facts were gathered"
    fid, v = min(candidates, key=lambda p: abs(abs(p[1]) - x) / max(abs(p[1]), 1))
    return f"nearest fact {fid} = {v:g}"


def script_ok(text: str, lang: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    if lang == "en":
        return sum(ch.isascii() for ch in letters) / len(letters) >= 0.8
    if lang not in SCRIPTS:
        return True
    lo, hi = SCRIPTS[lang]
    return sum(lo <= ord(ch) <= hi for ch in letters) / len(letters) >= 0.5


def check(adv: dict, ev: EvidenceStore, signals: list[Signal], language: str, question: str) -> GateResult:
    res = GateResult(True)

    # 1. Schema
    for key in ("headline", "summary"):
        if not isinstance(adv.get(key), str) or not adv[key].strip():
            res.add("schema", f"'{key}' is missing or empty")
    if len(adv.get("headline") or "") > 160:
        res.add("schema", "headline is longer than 120 characters")
    actions = adv.get("actions") or []
    if not actions:
        res.add("schema", "at least one action is required")
    for i, a in enumerate(actions):
        if a.get("when") not in WHEN:
            res.add("schema", f"actions[{i}].when must be one of {sorted(WHEN)}")
        if not a.get("evidence"):
            res.add("citations", f"actions[{i}] cites no evidence; every action needs at least one fact id")
    for i, r in enumerate(adv.get("risks") or []):
        if r.get("level") not in LEVELS:
            res.add("schema", f"risks[{i}].level must be low, moderate or high")
    if adv.get("confidence") not in ("low", "medium", "high"):
        res.add("schema", "confidence must be low, medium or high")

    # 2. Citations exist
    cited = [e for a in actions for e in a.get("evidence") or []]
    cited += [e for r in adv.get("risks") or [] for e in r.get("evidence") or []]
    cited += adv.get("market_evidence") or []
    unknown = sorted({c for c in cited if ev.get(c) is None})
    if unknown:
        res.add("citations", f"these ids are not in the tool results: {', '.join(unknown[:8])}. Use ids exactly as returned (see id_pattern).")

    # 3. Number grounding
    allowed = allowed_numbers(ev, signals, question)
    texts = [("headline", adv.get("headline") or ""), ("summary", adv.get("summary") or ""), ("market_advice", adv.get("market_advice") or "")]
    texts += [(f"actions[{i}]", f"{a.get('action', '')} {a.get('why', '')}") for i, a in enumerate(actions)]
    bad = []
    for where, text in texts:
        for x in extract_numbers(text):
            if not grounded(x, allowed):
                bad.append(f"{where}: '{x:g}' matches no fact ({nearest(x, allowed)})")
    if bad:
        res.add("number_grounding", "; ".join(bad[:6]) + ". Use only numbers from tool results (you may round them); don't convert units.")

    # 4. Risk agreement with the engine
    stated = {r.get("type"): r.get("level") for r in adv.get("risks") or []}
    for s in signals:
        if s.type not in ENFORCED_RISKS:
            continue
        mine = stated.get(s.type)
        if s.level in ("moderate", "high") and mine is None:
            res.add("risk_agreement", f"the evidence shows a {s.level} {s.type} risk ({s.detail}) but the advisory doesn't mention it")
        elif mine in LEVELS and abs(LEVELS.index(mine) - LEVELS.index(s.level)) > 1:
            res.add("risk_agreement", f"{s.type} stated as {mine}, but the evidence puts it at {s.level} ({s.detail})")

    # 5. Data gaps disclosed
    unavailable = sorted({r.tool for r in ev.results if r.status == "unavailable"})
    gaps = adv.get("data_gaps") or []
    if unavailable and len(gaps) < len(unavailable):
        res.add("data_gaps", f"these sources were unavailable and must be listed in data_gaps: {', '.join(unavailable)}")
    if adv.get("confidence") == "high" and (len(unavailable) >= 2 or "get_weather_forecast" in unavailable):
        res.add("data_gaps", "confidence can't be high when the weather forecast or two or more sources are missing")

    # 6. Safety: no chemical dosages
    all_text = " ".join(t for _, t in texts)
    if DOSE_RE.search(ascii_digits(all_text)):
        res.add("safety", "don't give chemical or fertiliser dosages; tell the farmer to follow the product label or ask the KVK")

    # 7. Language
    if not script_ok(f"{adv.get('headline', '')} {adv.get('summary', '')}", language):
        res.add("language", f"headline and summary must be written in the farmer's language ({language})")

    return res
