/* ============================================================
   NEXUS 2.0 — Hardcoded backend values
   Replace with real API calls later.
   ============================================================ */

/* ---------- The six agents, explained in plain language ---------- */
export const AGENTS = [
  {
    id: 'A1',
    name: 'Capture',
    tagline: 'Reads your files',
    status: 'healthy',
    version: 'v2',
    simple: 'Reads bank statements, SAP exports, Excel, CSV and PDF files — and pulls out the important numbers.',
    detail:
      'A1 is the data reader. It opens files from your bank, SAP, spreadsheets and PDF documents, checks they are valid, and extracts every transaction with a confidence score. Suspicious or unreadable files are quarantined — never silently processed.',
    reads: ['SAP exports', 'Excel', 'CSV', 'PDF documents', 'Bank statements'],
    icon: '📥',
  },
  {
    id: 'A2',
    name: 'Harmonize',
    tagline: 'Makes everything speak the same language',
    status: 'healthy',
    version: 'v3',
    simple: 'Converts different file formats and column names into one standard finance format.',
    detail:
      'Every bank and system names columns differently — "Posting Dt" vs "posting_date", "Amt" vs "amount". A2 translates them all into one standard finance format so the rest of the platform always knows what it is looking at.',
    reads: ['Column mapping', 'Date & currency normalization', 'Account mapping', 'Duplicate detection'],
    icon: '🔄',
  },
  {
    id: 'A3',
    name: 'Match',
    tagline: 'Finds the pairs',
    status: 'healthy',
    version: 'v3',
    simple: 'Automatically matches bank lines to GL entries, invoices to purchase orders, payments to invoices.',
    detail:
      'A3 compares two sets of records and finds which ones belong together. It tries exact matching first (same amount, same reference), then fuzzy matching (close amounts, close dates). Every match comes with a score and evidence.',
    reads: ['Bank ↔ GL matching', 'Invoice ↔ PO matching', 'Partial payments', 'Duplicate detection'],
    icon: '🔗',
  },
  {
    id: 'A4',
    name: 'Validate',
    tagline: 'Checks the rules',
    status: 'healthy',
    version: 'v2',
    simple: 'Applies your finance rules and tolerances, then recommends: matched, needs review, or exception.',
    detail:
      'A4 runs the approved rulebook: tolerance checks, materiality thresholds, duplicate and policy rules. It never approves anything by itself — it recommends an outcome and stops for a human when the rules say so.',
    reads: ['Tolerance checks', 'Materiality rules', 'Severity classification', 'Recommendations'],
    icon: '🛡️',
  },
  {
    id: 'A5',
    name: 'Explain',
    tagline: 'Turns results into reports',
    status: 'healthy',
    version: 'v1',
    simple: 'Creates reports and explains every number — showing exactly which source records support it.',
    detail:
      'A5 writes the reconciliation report, the exception summary, the variance explanation. Every figure links back to the source rows and calculations used, so you can always answer "where did this number come from?".',
    reads: ['Reconciliation reports', 'Variance explanations', 'Evidence links', 'Management summaries'],
    icon: '📊',
  },
  {
    id: 'A6',
    name: 'Coordinate',
    tagline: 'Gets the right human involved',
    status: 'degraded',
    version: 'v2',
    simple: 'Sends anything unusual to the right person for review, collects their decision, and keeps things moving.',
    detail:
      'When something cannot be completed safely, A6 creates a review task, assigns it to the right team, sends notifications, and collects the decision — accept, reject, correct, or request more information. Overdue items escalate automatically.',
    reads: ['Review queues', 'Notifications', 'Human decisions', 'Escalations'],
    icon: '🧭',
  },
  {
    id: 'A7',
    name: 'OCR Engine',
    tagline: 'Reads documents like a human',
    status: 'dev',
    version: 'v0.1 beta',
    simple: 'Extracts structured data from scanned invoices, receipts and PDF documents using advanced optical character recognition.',
    detail: 'A7 is under active development. It will use computer vision and LLMs to extract structured data from unstructured documents.',
    reads: ['Scanned invoices', 'PDF documents', 'Handwritten notes', 'Image files'],
    icon: '🔬',
  },
]

/* ---------- Platform services health ---------- */
export const SERVICES = [
  { name: 'Workflow Orchestrator', status: 'ok', detail: 'All runs executing normally', version: 'v4.1' },
  { name: 'Rule Engine', status: 'ok', detail: 'v2.4 · 38 approved rules' },
  { name: 'Calculation Engine', status: 'ok', detail: 'v1.9 · 12 formulas' },
  { name: 'Master Data Service', status: 'ok', detail: 'Synced 04:00 today' },
  { name: 'Exception Service', status: 'ok', detail: '7 open items' },
  { name: 'Audit & Lineage', status: 'ok', detail: 'Append-only · healthy' },
]

/* ---------- Dashboard KPIs ---------- */
export const KPIS = [
  { id: 'total', label: 'Total Super Agents', value: '12', delta: '+3 this month', up: true, icon: '🤖' },
  { id: 'published', label: 'Published', value: '7', delta: 'Live in production', up: true, icon: '🚀' },
  { id: 'draft', label: 'In Draft', value: '4', delta: '2 pending review', up: false, icon: '📝' },
  { id: 'popular', label: 'Most Active Today', value: 'Budget vs Actual', delta: '48 runs today', up: true, icon: '⚡' },
]

/* ---------- Charts ---------- */
export const CHART_BARS = [42, 58, 45, 68, 55, 74, 62, 80, 71, 88, 78, 92]
export const DONUT_SEGMENTS = [
  { label: 'Auto-matched', value: 92, color: '#34d399' },
  { label: 'Needs review', value: 6, color: '#fbbf24' },
  { label: 'Exceptions', value: 2, color: '#f87171' },
]

export const ACTIVITY = [
  { icon: '✓', text: 'Bank-to-GL run completed — 412 matches, 3 exceptions', time: '10:30', tone: 'ok' },
  { icon: '⚑', text: 'Exception exc-10045 assigned to Marcus Chen', tone: 'warn', at: '10:32' },
  { icon: '📥', text: 'bank-statement-aug.xlsx captured (450 rows)', at: '10:25', tone: 'ok' },
  { icon: '⚙', text: 'Rule "bank_difference_tolerance" updated to v2', at: '09:58', tone: 'ok' },
  { icon: '⚠', text: 'A6 notification queue degraded — investigating', at: '09:41', tone: 'err' },
]

/* ---------- Users (for Users page) ---------- */
export const USERS = [
  { id: 'usr-001', name: 'Elena Vance', email: 'admin@nexus.io', role: 'Finance Admin', entities: '1000, 2000', status: 'active', lastActive: '2 min ago' },
  { id: 'usr-017', name: 'Marcus Chen', email: 'reviewer@aurum.io', role: 'Finance Reviewer', entities: '1000', status: 'active', lastActive: '18 min ago' },
  { id: 'usr-023', name: 'Priya Nair', email: 'priya.nair@aurum.io', role: 'Finance Reviewer', entities: '2000', status: 'active', lastActive: '1 hr ago' },
  { id: 'usr-031', name: 'Tom Okafor', email: 'tom.okafor@aurum.io', role: 'Viewer', entities: '1000', status: 'invited', lastActive: '—' },
]

export const ROLES = ['Finance Admin', 'Finance Reviewer', 'Finance User', 'Super Admin']

/* ---------- Rules & calculations registry (for Create Agent) ---------- */
export const RULES = [
  { id: 'bank_difference_tolerance', name: 'Bank Difference Tolerance', version: 2, desc: 'Flags differences above $50.00' },
  { id: 'materiality_threshold', version: 3, name: 'Materiality Threshold', desc: 'Items above $10,000 need review' },
  { id: 'duplicate_payment_check', version: 1, name: 'Duplicate Payment Check', desc: 'Flags same vendor + amount within 7 days' },
  { id: 'currency_conversion_rule', version: 2, name: 'Currency Conversion', desc: 'Uses approved ECB daily rates' },
]

export const CALCULATIONS = [
  { id: 'calculate_reconciliation_difference', name: 'Reconciliation Difference', version: 1, desc: 'Bank balance minus GL balance' },
  { id: 'calculate_variance_percent', name: 'Variance %', version: 1, desc: 'Percentage change between periods' },
  { id: 'calculate_match_score', name: 'Match Score', version: 3, desc: 'Weighted score from amount, date and reference' },
]

/* ---------- Create Agent wizard: suggested workflow (mock LLM) ---------- */
export const SUGGESTED_WORKFLOW = {
  summary: 'Based on your description, I recommend a Bank-to-GL Reconciliation workflow.',
  agents: ['A1', 'A2', 'A3', 'A4', 'A5', 'A6'],
  reasoning:
    'You described matching bank statement lines against SAP GL balances with human review for differences. This maps to the Reconciliation template: capture both sources, harmonize them, match, validate tolerances, and route exceptions to reviewers.',
  confidence: 94,
}

export const SOURCE_TYPES = ['SAP export', 'Excel', 'CSV', 'PDF document', 'API']

export const fmtMoney = (n) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })