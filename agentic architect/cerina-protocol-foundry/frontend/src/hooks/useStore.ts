import { create } from 'zustand';
import type {
  ProtocolState,
  ProtocolSummary,
  WSMessage,
  WSAgentUpdate,
  WSStateUpdate,
} from '../types';

interface CerinaStore {
  // Current protocol being viewed/edited
  currentProtocol: ProtocolState | null;
  setCurrentProtocol: (protocol: ProtocolState | null) => void;

  // Protocol list
  protocols: ProtocolSummary[];
  setProtocols: (protocols: ProtocolSummary[]) => void;
  addProtocol: (protocol: ProtocolSummary) => void;

  // Active agent tracking
  activeAgents: Record<string, WSAgentUpdate>;
  updateAgentStatus: (threadId: string, update: WSAgentUpdate) => void;

  // WebSocket state updates
  handleStateUpdate: (update: WSStateUpdate) => void;

  // UI state
  isCreating: boolean;
  setIsCreating: (creating: boolean) => void;

  isApproving: boolean;
  setIsApproving: (approving: boolean) => void;

  error: string | null;
  setError: (error: string | null) => void;

  // Edit mode for human review
  editMode: boolean;
  setEditMode: (editMode: boolean) => void;
  draftEdits: string;
  setDraftEdits: (edits: string) => void;

  // Human feedback
  humanFeedback: string;
  setHumanFeedback: (feedback: string) => void;

  // Connection status
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
}

export const useCerinaStore = create<CerinaStore>((set, get) => ({
  // Current protocol
  currentProtocol: null,
  setCurrentProtocol: (protocol) => set({ currentProtocol: protocol }),

  // Protocol list
  protocols: [],
  setProtocols: (protocols) => set({ protocols }),
  addProtocol: (protocol) =>
    set((state) => ({
      protocols: [protocol, ...state.protocols],
    })),

  // Active agents
  activeAgents: {},
  updateAgentStatus: (threadId, update) =>
    set((state) => ({
      activeAgents: {
        ...state.activeAgents,
        [threadId]: update,
      },
    })),

  // State updates from WebSocket
  handleStateUpdate: (update) => {
    const { currentProtocol } = get();
    if (currentProtocol && currentProtocol.thread_id === update.thread_id) {
      set({
        currentProtocol: {
          ...currentProtocol,
          active_agent: update.active_agent as ProtocolState['active_agent'],
          approval_status: update.approval_status as ProtocolState['approval_status'],
          iteration_count: update.iteration_count,
          safety_score: update.safety_score,
          clinical_score: update.clinical_score,
          empathy_scores: {
            ...currentProtocol.empathy_scores,
            overall: update.empathy_overall,
          },
          current_draft: update.current_draft_preview || currentProtocol.current_draft,
        },
      });
    }
  },

  // UI state
  isCreating: false,
  setIsCreating: (creating) => set({ isCreating: creating }),

  isApproving: false,
  setIsApproving: (approving) => set({ isApproving: approving }),

  error: null,
  setError: (error) => set({ error }),

  // Edit mode
  editMode: false,
  setEditMode: (editMode) => set({ editMode }),
  draftEdits: '',
  setDraftEdits: (edits) => set({ draftEdits: edits }),

  // Human feedback
  humanFeedback: '',
  setHumanFeedback: (feedback) => set({ humanFeedback: feedback }),

  // WebSocket connection
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));

// Selector hooks for specific pieces of state
export const useCurrentProtocol = () => useCerinaStore((state) => state.currentProtocol);
export const useProtocols = () => useCerinaStore((state) => state.protocols);
export const useIsCreating = () => useCerinaStore((state) => state.isCreating);
export const useError = () => useCerinaStore((state) => state.error);
export const useWsConnected = () => useCerinaStore((state) => state.wsConnected);
