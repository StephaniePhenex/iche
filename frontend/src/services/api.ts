/**
 * api.ts — All backend calls.
 *
 * MOCK MODE: When VITE_API_URL is not set, every call returns simulated
 * responses so the UI works without a running Python backend.
 */

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? "";
const USE_MOCK = !BASE;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RegisterResult {
  approved: boolean;
  message: string;
}

export interface LoginResult {
  token: string;
}

export interface AgentOutput {
  agent: string;
  solution: string;
  confidence: number;
  analysis: string;
}

export interface Iteration {
  number: number;
  conflicts: number;
  avg_confidence: number;
  agents: AgentOutput[];
}

export interface ChatResult {
  response: string;
  structured_output: {
    iterations: Iteration[];
    final_solution: string;
    confidence: number;
    why_this: string[];
    rejected_options: string[];
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const token = sessionStorage.getItem("token");
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message ?? "Request failed");
  }
  return res.json();
}

// ── Mock data generators ──────────────────────────────────────────────────────

function mockRegister(username: string): RegisterResult {
  // 70% approval rate to demonstrate the pending/rejected states.
  const roll = Math.random();
  if (roll < 0.15) {
    return { approved: false, message: "Registration rejected: username already taken." };
  }
  if (roll < 0.30) {
    return { approved: false, message: "Registration pending admin review. You'll be notified." };
  }
  return { approved: true, message: `Welcome, ${username}! Your account is ready.` };
}

function mockLogin(): LoginResult {
  // Generate a fake JWT-like token.
  const payload = btoa(JSON.stringify({ sub: "mock_user", iat: Date.now() }));
  return { token: `mock.${payload}.signature` };
}

/** Heuristic: demo itinerary when no backend — not from a live model. */
function isMockOkinawaTripQuery(q: string): boolean {
  const s = q.trim();
  if (!s) return false;
  const okinawa = /冲绳|沖繩|琉球/i.test(s);
  const trip = /行程|旅游|旅行|攻略|度假|玩/.test(s) || /\d\s*天|五天|七日|一周/.test(s);
  return okinawa && trip;
}

function mockOkinawaAgents(userLine: string): AgentOutput[] {
  const wantAmericanVillage = /美国村|美國村|北谷|北谷町/i.test(userLine);
  const day2 = wantAmericanVillage
    ? "美国村（北谷）— 海滨、日落、餐饮集中；住附近可减少折返。"
    : "中部 — 嘉手纳展望台或东南植物园一带，傍晚可到美国村用餐（若未安排住宿可改为那霸往返）。";

  const plan = [
    "第1天：抵达那霸 → 酒店入住 → 国际通散步晚餐（轻松适应时差与气候）。",
    `第2天：${day2}`,
    "第3天：北部 — 美丽海水族馆、古宇利大桥一带（车程长，早出晚归；旺季先订票）。",
    "第4天：离岛或海滩日 — 庆良间诸岛浮潜/潜水（视海况）或南部知念岬、斋场御岳文化线。",
    "第5天：那霸购物/首里城公园 → 机场（预留还车与国际线提前量）。",
  ].join("\n");

  return [
    {
      agent: "System Architect",
      solution: `【示例 5 日冲绳骨架行程】（mock 演示，出行前请自行核对开放时间与预约）\n\n${plan}`,
      confidence: 0.84,
      analysis:
        "按「抵达缓冲 → 中部/美国村 → 北部大景点 → 离岛或南部 → 离开日」排布，减少走回头路。",
    },
    {
      agent: "Critical Analyst",
      solution:
        "风险提示：黄金周/连假租车与水族馆极难订；北部单程车程常 1.5h+；紫外线与台风季需备用室内方案。建议确认是否自驾及酒店取消政策。",
      confidence: 0.79,
      analysis:
        "把「能否早起」「是否带娃/老人」「预算档位」问清之前，不要锁死离岛与潜水项目。",
    },
    {
      agent: "Divergent Thinker",
      solution:
        "若不想赶北部：可把第3天换成「浦添大公园 + Outlet + 中部海滩」，北部压缩为半日展望；或把离岛改到渡嘉敷一日。",
      confidence: 0.72,
      analysis:
        "天气差时优先换室内（博物馆、DFS、商场）并保留美国村夜景为弹性块。",
    },
  ];
}

function mockChat(message: string): ChatResult {
  const lower = message.toLowerCase();
  const topic =
    message.trim().length > 200 ? `${message.trim().slice(0, 200)}…` : message.trim() || "(empty prompt)";

  const okinawaDemo = isMockOkinawaTripQuery(message);
  const agents: AgentOutput[] = okinawaDemo
    ? mockOkinawaAgents(message)
    : [
        {
          agent: "System Architect",
          solution: `Structured plan with clear priorities and day-by-day constraints for: "${topic}"`,
          confidence: 0.82,
          analysis:
            "Favors an ordered breakdown (constraints first, then activities) so tradeoffs stay visible.",
        },
        {
          agent: "Critical Analyst",
          solution: `Validate assumptions (timing, budget, mobility, weather) before locking details for: "${topic}"`,
          confidence: 0.78,
          analysis:
            "Calls out unstated risks and suggests checkpoints so the plan survives real-world friction.",
        },
        {
          agent: "Divergent Thinker",
          solution: `Alternate ordering or backup options if one day slips — still centered on: "${topic}"`,
          confidence: 0.71,
          analysis:
            "Keeps flexibility without abandoning the core goal; useful when external factors shift.",
        },
      ];

  const isSimple =
    lower.includes("what") || lower.includes("which") || lower.includes("should");

  const iterations: Iteration[] = isSimple
    ? [
        { number: 1, conflicts: 2, avg_confidence: 0.77, agents },
        { number: 2, conflicts: 1, avg_confidence: 0.84, agents },
      ]
    : [
        { number: 1, conflicts: 3, avg_confidence: 0.77, agents },
        { number: 2, conflicts: 2, avg_confidence: 0.81, agents },
        { number: 3, conflicts: 1, avg_confidence: 0.87, agents },
      ];

  const structured_output = okinawaDemo
    ? {
        iterations,
        final_solution: agents[0].solution,
        confidence: 0.85,
        why_this: [
          "日程按地理动线拆分，减少那霸—北部反复折返",
          "第2天可贴合「美国村」等明确约束（若你在问题里提到）",
          "预留离开日与海况/旺季的弹性说明",
        ],
        rejected_options: [
          "五天里每天跨那霸—北部往返（车程与时间成本高）",
          "离岛与北部水族馆都塞满且不留缓冲（遇坏天气易全盘崩）",
        ],
      }
    : {
        iterations,
        final_solution: agents[0].solution,
        confidence: 0.85,
        why_this: [
          "Best fit to the problem as stated",
          "Highest-confidence line among the three agents",
          "Tradeoffs deemed acceptable for the planning horizon",
        ],
        rejected_options: [
          "Single rigid schedule with no backup day",
          "Optimistic pacing with no buffer for delays",
        ],
      };

  return {
    response: okinawaDemo
      ? `Multi-agent deliberation complete (${iterations.length} iterations). 以下为前端 mock 示例行程，非实时检索；真实规划请接 /api/chat 或自行查证。`
      : `Multi-agent deliberation complete (${iterations.length} iterations). Convergence achieved. (Mock UI data — connect a real API for task-specific answers.)`,
    structured_output,
  };
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function register(username: string, password: string): Promise<RegisterResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return mockRegister(username);
  }
  return post<RegisterResult>("/api/register", { username, password });
}

export async function login(username: string, password: string): Promise<LoginResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 600));
    if (!username || !password) throw new Error("Username and password required");
    return mockLogin();
  }
  return post<LoginResult>("/api/login", { username, password });
}

export async function chat(message: string): Promise<ChatResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 1800 + Math.random() * 1000));
    return mockChat(message);
  }
  return post<ChatResult>("/api/chat", { message });
}
