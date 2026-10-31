export type Level = 'low' | 'moderate' | 'high'

export interface Fact {
  id: string
  label: string
  value: number | string
  unit: string
  provider: string
  url: string
  fetched_at: number
}

export interface ToolData {
  tool: string
  status: 'ok' | 'partial' | 'unavailable'
  providers_tried: string[]
  facts: Fact[]
  notes: string[]
  series: Record<string, any>
}

export interface Action {
  when: 'today' | 'next_3_days' | 'this_week' | 'before_harvest'
  action: string
  why: string
  evidence: string[]
}

export interface Advisory {
  headline: string
  summary: string
  actions: Action[]
  risks: { type: string; level: Level; evidence: string[] }[]
  market_advice?: string
  market_evidence?: string[]
  data_gaps: string[]
  confidence: 'low' | 'medium' | 'high'
  fallback?: boolean
  fallback_reason?: string
}

export interface Signal {
  type: string
  level: Level
  title: string
  detail: string
  action: string
  evidence: string[]
  threshold_source: string
}

export interface Stats {
  model: string
  tool_calls: number
  turns: number
  submissions: number
  first_pass: boolean | null
  repairs: number
  fallback: boolean
  latency_s: number
}

export type TraceEvent =
  | { event: 'start'; t: number; model: string; stage: any; crop_known: boolean; field: any }
  | { event: 'thought'; t: number; text: string }
  | { event: 'tool_start'; t: number; tool: string; args: Record<string, unknown>; id: string | null; fallback?: boolean }
  | { event: 'tool_end'; t: number; tool: string; id: string | null; status: ToolData['status']; ms: number; providers: string[]; notes: string[]; n_facts: number; data: ToolData }
  | { event: 'gate'; t: number; ok: boolean; attempt: number; problems: { check: string; detail: string }[] }
  | { event: 'llm_error'; t: number; message: string }
  | { event: 'advisory'; t: number; advisory: Advisory; signals: Signal[]; sources: Record<string, Fact>; language: string }
  | { event: 'done'; t: number; stats: Stats }
  | { event: 'error'; t?: number; message: string }

export interface Profile {
  lat: number | null
  lon: number | null
  place: string
  crop: string
  sowing_date: string
  language: string
}
