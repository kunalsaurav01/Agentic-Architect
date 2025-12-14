// Cerina Protocol Foundry - TypeScript Types

export interface EmpathyScores {
  warmth: number;
  accessibility: number;
  safety_language: number;
  cultural_sensitivity: number;
  overall: number;
  readability_grade?: string;
  suggestions: string[];
}

export interface SafetyFlag {
  id: string;
  flag_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  details: string;
  location?: string;
  resolved: boolean;
  recommendation?: string;
}

export interface ClinicalFeedback {
  id: string;
  agent: string;
  category: string;
  feedback: string;
  score?: number;
  suggestions: string[];
  iteration: number;
}

export interface DraftVersion {
  version: number;
  content: string;
  agent: string;
  timestamp: string;
  changes_summary?: string;
}

export interface DebateEntry {
  from_agent: string;
  to_agent?: string;
  message: string;
  message_type: 'critique' | 'suggestion' | 'agreement' | 'disagreement' | 'question';
  iteration: number;
  timestamp: string;
}

export interface SupervisorDecision {
  id: string;
  decision: string;
  reasoning: string;
  next_agent: string;
  should_continue: boolean;
  iteration: number;
  timestamp: string;
}

export type ApprovalStatus =
  | 'drafting'
  | 'in_review'
  | 'pending_human_review'
  | 'human_editing'
  | 'approved'
  | 'rejected';

export type AgentName =
  | 'supervisor'
  | 'drafting'
  | 'clinical_critic'
  | 'safety_guardian'
  | 'empathy'
  | 'human_review';

export interface ProtocolState {
  thread_id: string;
  protocol_id: string;
  user_intent: string;
  current_draft?: string;
  draft_versions: DraftVersion[];
  safety_flags: SafetyFlag[];
  safety_score: number;
  clinical_feedback: ClinicalFeedback[];
  clinical_score: number;
  empathy_scores: EmpathyScores;
  iteration_count: number;
  max_iterations: number;
  approval_status: ApprovalStatus;
  active_agent: AgentName;
  created_at: string;
  updated_at: string;
}

export interface ProtocolSummary {
  protocol_id: string;
  thread_id: string;
  user_intent: string;
  status: ApprovalStatus;
  safety_score: number;
  clinical_score: number;
  iteration_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowHistory {
  thread_id: string;
  debate_history: DebateEntry[];
  supervisor_decisions: SupervisorDecision[];
  agent_notes: Record<string, Array<{ note: string; timestamp: string; iteration: number }>>;
}

// WebSocket message types
export interface WSMessage {
  type: 'agent_update' | 'state_update' | 'human_review_required' | 'protocol_complete' | 'error' | 'ping' | 'pong' | 'connected' | 'subscribed';
  data: Record<string, unknown>;
  timestamp: string;
}

export interface WSAgentUpdate {
  agent: AgentName;
  status: 'starting' | 'processing' | 'complete' | 'error';
  message?: string;
  iteration: number;
}

export interface WSStateUpdate {
  thread_id: string;
  active_agent: AgentName;
  approval_status: ApprovalStatus;
  iteration_count: number;
  safety_score: number;
  clinical_score: number;
  empathy_overall: number;
  current_draft_preview?: string;
}

// API request/response types
export interface CreateProtocolRequest {
  user_intent: string;
  additional_context?: string;
}

export interface ApproveProtocolRequest {
  approved: boolean;
  feedback?: string;
  edits?: string;
}
