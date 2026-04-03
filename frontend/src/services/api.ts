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

export interface Evidence {
  source: string;
  content: string;
}

export interface PlanStep {
  step: string;
  description: string;
}

export interface Conflict {
  id: number;
  type: string;
  agents_involved: string[];
  description: string;
  resolution_suggestion: string;
}

export interface ResearcherOutput {
  agent: "Researcher";
  evidence: Evidence[];
  tool_used: string[];
}

export interface PlannerOutput {
  agent: "Planner+Synthesizer";
  proposed_plan: PlanStep[];
  final_choice: string;
  reasoning: string;
  tool_used: string[];
}

export interface CriticOutput {
  agent: "Critic";
  conflicts: Conflict[];
  resolved: string[];
  unresolved: string[];
  key_conflicts_prioritized: boolean;
  tool_used: string[];
}

export interface PreviousRound {
  final_choice: string;
  reasoning: string;
  unresolved_issues: string[];
}

export type AgentOutput = ResearcherOutput | PlannerOutput | CriticOutput;

export interface Iteration {
  iteration_number: number;
  agents: AgentOutput[];
  metadata: {
    timestamp: string;
    token_usage: string;
    cost: string;
    latency: string;
  };
}

export interface ChatResult {
  response: string;
  structured_output: {
    iterations: Iteration[];
    final_choice: string;
    reasoning: string;
    unresolved_issues: string[];
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
  const roll = Math.random();
  if (roll < 0.15) return { approved: false, message: "Registration rejected: username already taken." };
  if (roll < 0.30) return { approved: false, message: "Registration pending admin review. You'll be notified." };
  return { approved: true, message: `Welcome, ${username}! Your account is ready.` };
}

function mockLogin(): LoginResult {
  const payload = btoa(JSON.stringify({ sub: "mock_user", iat: Date.now() }));
  return { token: `mock.${payload}.signature` };
}

function mockChat(message: string): ChatResult {
  const topic = message.trim().slice(0, 120) || "(empty prompt)";

  const researcher: ResearcherOutput = {
    agent: "Researcher",
    evidence: [
      { source: "domain knowledge", content: `Key context for "${topic}": successful approaches require clear goals with measurable success criteria established upfront.` },
      { source: "general knowledge", content: "Common pitfalls: underestimating complexity, skipping validation steps, and not accounting for hard constraints." },
      { source: "expert consensus", content: "Iterative/phased approaches consistently outperform big-bang execution in uncertain environments — validate assumptions early." },
      { source: "user context", content: "The specific constraints you have shape which options are viable. Fixed constraints must be respected; flexible ones can be negotiated." },
    ],
    tool_used: ["DomainKnowledge", "WebSearch"],
  };

  const planner: PlannerOutput = {
    agent: "Planner+Synthesizer",
    proposed_plan: [
      { step: "Step 1: Clarify objectives", description: "Define specific, measurable goals. Identify success criteria and hard constraints upfront." },
      { step: "Step 2: Map constraints and resources", description: "Inventory time, budget, skills, and dependencies. Distinguish fixed from flexible constraints." },
      { step: "Step 3: Generate and evaluate options", description: "Develop 2–3 concrete approaches using available evidence. Evaluate each against goals and constraints." },
      { step: "Step 4: Execute with milestones", description: "Break the chosen approach into concrete actions with checkpoints to catch problems early." },
      { step: "Step 5: Build contingencies", description: "Identify top 2–3 failure modes and prepare fallback actions for each." },
    ],
    final_choice: `For "${topic}": adopt a phased, iterative approach — start with a minimal viable version, validate it against real constraints, then expand. This balances speed with risk management and allows course-correction before full commitment.`,
    reasoning: "A phased approach reduces commitment risk, allows early validation, and adapts as new information emerges. Full upfront planning fails when initial assumptions prove wrong.",
    tool_used: ["Reasoning", "Calculator"],
  };

  const critic1: CriticOutput = {
    agent: "Critic",
    conflicts: [
      {
        id: 1,
        type: "logic_conflict",
        agents_involved: ["Planner+Synthesizer", "Researcher"],
        description: "Planner treats phased approach as inherently lower-risk, but Researcher evidence shows phased rollouts can accumulate debt if phase boundaries aren't explicitly defined.",
        resolution_suggestion: "Define explicit phase boundaries and acceptance criteria to prevent debt accumulation between phases.",
      },
      {
        id: 2,
        type: "fact_conflict",
        agents_involved: ["Researcher", "Planner+Synthesizer"],
        description: "Researcher flags 'underestimating complexity' as a top failure mode, but no explicit complexity estimation step appears in the plan.",
        resolution_suggestion: "Add an explicit complexity estimation step, or expand Step 2 to include it before option generation.",
      },
    ],
    resolved: [],
    unresolved: [
      "Phase boundary definition missing — risk of technical debt accumulation",
      "Complexity estimation absent from proposed plan steps",
    ],
    key_conflicts_prioritized: true,
    tool_used: ["ConflictAnalysis", "LogicCheck"],
  };

  const critic2: CriticOutput = {
    agent: "Critic",
    conflicts: [
      {
        id: 1,
        type: "preference_conflict",
        agents_involved: ["Planner+Synthesizer", "Researcher"],
        description: "Plan milestones are still partially time-based. Evidence supports outcome-based criteria as more reliable indicators of readiness.",
        resolution_suggestion: "Replace time-only milestones with outcome-based success criteria (e.g., 'validate N assumptions' rather than 'complete in 4 weeks').",
      },
    ],
    resolved: [
      "Phase boundary definition: resolved — Step 1 now explicitly defines phase boundaries",
      "Complexity estimation: resolved — embedded in scope refinement step",
    ],
    unresolved: ["Milestones partially time-based — should be primarily outcome-based"],
    key_conflicts_prioritized: true,
    tool_used: ["ConflictAnalysis"],
  };

  const critic3: CriticOutput = {
    agent: "Critic",
    conflicts: [],
    resolved: [
      "Phase boundary definition: resolved",
      "Complexity estimation: resolved",
      "Milestone criteria: resolved — final plan uses outcome-based success criteria",
    ],
    unresolved: [],
    key_conflicts_prioritized: true,
    tool_used: ["ConflictAnalysis"],
  };

  const iterations: Iteration[] = [
    {
      iteration_number: 1,
      agents: [researcher, planner, critic1],
      metadata: { timestamp: new Date().toISOString(), token_usage: "", cost: "", latency: "mock" },
    },
    {
      iteration_number: 2,
      agents: [researcher, { ...planner, final_choice: `Refined for "${topic}": two-phase approach — Phase 1 validates core assumptions (outcome-based); Phase 2 scales with confidence from Phase 1 learnings.` }, critic2],
      metadata: { timestamp: new Date().toISOString(), token_usage: "", cost: "", latency: "mock" },
    },
    {
      iteration_number: 3,
      agents: [researcher, { ...planner, final_choice: `Final for "${topic}": two-phase phased approach with outcome-based validation gates. Phase 1 validates at low cost; Phase 2 scales with confidence. All conflicts resolved.` }, critic3],
      metadata: { timestamp: new Date().toISOString(), token_usage: "", cost: "", latency: "mock" },
    },
  ];

  return {
    response: `Multi-agent deliberation complete (3 iterations). (Mock UI data — connect /api/chat for live answers.)`,
    structured_output: {
      iterations,
      final_choice: `Final for "${topic}": two-phase phased approach with outcome-based validation gates. Phase 1 validates core assumptions at low cost; Phase 2 scales with confidence. All conflicts resolved.`,
      reasoning: "Full convergence achieved. Approach is pragmatic, risk-aware, and achievable within realistic constraints. Phased structure provides flexibility while maintaining clear direction.",
      unresolved_issues: [],
    },
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

export async function chat(message: string, previousRound?: PreviousRound): Promise<ChatResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 1800 + Math.random() * 1000));
    return mockChat(message);
  }
  return post<ChatResult>("/api/chat", {
    message,
    ...(previousRound ? { previous_round: previousRound } : {}),
  });
}
