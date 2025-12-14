import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

import { CreateProtocolForm } from '../components/CreateProtocolForm';
import { AgentStatus } from '../components/AgentStatus';
import { QualityScores } from '../components/QualityScores';
import { ProtocolViewer } from '../components/ProtocolViewer';
import { HumanReviewPanel } from '../components/HumanReviewPanel';
import { DebateHistory } from '../components/DebateHistory';

import { useCerinaStore } from '../hooks/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  createProtocol,
  getProtocol,
  approveProtocol,
  getProtocolHistory,
} from '../utils/api';
import type { WSMessage, ProtocolState, WorkflowHistory } from '../types';
import { cn } from '../utils/cn';

export function Dashboard() {
  const navigate = useNavigate();
  const {
    currentProtocol,
    setCurrentProtocol,
    isCreating,
    setIsCreating,
    isApproving,
    setIsApproving,
    error,
    setError,
    editMode,
    setEditMode,
    draftEdits,
    setDraftEdits,
    humanFeedback,
    setHumanFeedback,
    wsConnected,
    setWsConnected,
    handleStateUpdate,
    updateAgentStatus,
  } = useCerinaStore();

  const [workflowHistory, setWorkflowHistory] = useState<WorkflowHistory | null>(null);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  // WebSocket handler
  const handleWSMessage = useCallback(
    (message: WSMessage) => {
      console.log('WS Message:', message);

      switch (message.type) {
        case 'agent_update':
          if (currentProtocol) {
            updateAgentStatus(
              currentProtocol.thread_id,
              message.data as any
            );
          }
          break;

        case 'state_update':
          handleStateUpdate(message.data as any);
          break;

        case 'human_review_required':
          // Refresh the full protocol state
          if (currentProtocol) {
            refreshProtocol(currentProtocol.thread_id);
          }
          break;

        case 'protocol_complete':
          if (currentProtocol) {
            refreshProtocol(currentProtocol.thread_id);
          }
          break;

        case 'error':
          setError(message.data.error as string);
          break;
      }
    },
    [currentProtocol, handleStateUpdate, updateAgentStatus, setError]
  );

  const { isConnected, subscribe } = useWebSocket({
    threadId: currentProtocol?.thread_id,
    onMessage: handleWSMessage,
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
  });

  // Refresh protocol from API
  const refreshProtocol = async (threadId: string) => {
    try {
      const [protocol, history] = await Promise.all([
        getProtocol(threadId),
        getProtocolHistory(threadId).catch(() => null),
      ]);
      setCurrentProtocol(protocol);
      if (history) setWorkflowHistory(history);
    } catch (err) {
      console.error('Failed to refresh protocol:', err);
    }
  };

  // Poll for updates when not connected via WebSocket
  useEffect(() => {
    if (!currentProtocol) return;

    const needsPolling =
      !isConnected &&
      currentProtocol.approval_status !== 'approved' &&
      currentProtocol.approval_status !== 'rejected';

    if (needsPolling) {
      const interval = setInterval(() => {
        refreshProtocol(currentProtocol.thread_id);
      }, 3000);
      setPollInterval(interval);
      return () => clearInterval(interval);
    } else if (pollInterval) {
      clearInterval(pollInterval);
      setPollInterval(null);
    }
  }, [currentProtocol, isConnected]);

  // Subscribe to WebSocket when protocol changes
  useEffect(() => {
    if (currentProtocol && isConnected) {
      subscribe(currentProtocol.thread_id);
    }
  }, [currentProtocol?.thread_id, isConnected, subscribe]);

  // Create new protocol
  const handleCreateProtocol = async (
    userIntent: string,
    additionalContext?: string
  ) => {
    setIsCreating(true);
    setError(null);

    try {
      const protocol = await createProtocol({
        user_intent: userIntent,
        additional_context: additionalContext,
      });
      setCurrentProtocol(protocol);

      // Start polling/watching for updates
      if (isConnected) {
        subscribe(protocol.thread_id);
      }

      // Fetch history
      const history = await getProtocolHistory(protocol.thread_id).catch(
        () => null
      );
      if (history) setWorkflowHistory(history);
    } catch (err: any) {
      setError(err.message || 'Failed to create protocol');
    } finally {
      setIsCreating(false);
    }
  };

  // Approve protocol
  const handleApprove = async (feedback?: string, edits?: string) => {
    if (!currentProtocol) return;
    setIsApproving(true);
    setError(null);

    try {
      const result = await approveProtocol(currentProtocol.thread_id, {
        approved: true,
        feedback,
        edits,
      });
      setCurrentProtocol(result);
      setEditMode(false);
      setDraftEdits('');
      setHumanFeedback('');
    } catch (err: any) {
      setError(err.message || 'Failed to approve protocol');
    } finally {
      setIsApproving(false);
    }
  };

  // Request revision
  const handleReject = async (feedback: string, edits?: string) => {
    if (!currentProtocol) return;
    setIsApproving(true);
    setError(null);

    try {
      const result = await approveProtocol(currentProtocol.thread_id, {
        approved: false,
        feedback,
        edits,
      });
      setCurrentProtocol(result);
      setEditMode(false);
      setDraftEdits('');
      setHumanFeedback('');
    } catch (err: any) {
      setError(err.message || 'Failed to request revision');
    } finally {
      setIsApproving(false);
    }
  };

  // Reset to create new
  const handleReset = () => {
    setCurrentProtocol(null);
    setWorkflowHistory(null);
    setEditMode(false);
    setDraftEdits('');
    setHumanFeedback('');
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Cerina Protocol Foundry
              </h1>
              <p className="text-sm text-gray-500">
                Multi-Agent CBT Protocol Design System
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Connection status */}
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
                  wsConnected
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-500'
                )}
              >
                {wsConnected ? (
                  <Wifi className="w-4 h-4" />
                ) : (
                  <WifiOff className="w-4 h-4" />
                )}
                {wsConnected ? 'Connected' : 'Disconnected'}
              </div>

              {/* New protocol button */}
              {currentProtocol && (
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 px-4 py-2 bg-cerina-600 text-white rounded-lg hover:bg-cerina-700 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  New Protocol
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <span className="text-red-700">{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {!currentProtocol ? (
          /* Create form */
          <div className="max-w-2xl mx-auto">
            <CreateProtocolForm
              onSubmit={handleCreateProtocol}
              isLoading={isCreating}
            />
          </div>
        ) : (
          /* Protocol view */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column - Protocol viewer */}
            <div className="lg:col-span-2 space-y-6">
              <div className="h-[600px]">
                <ProtocolViewer
                  currentDraft={currentProtocol.current_draft || ''}
                  draftVersions={currentProtocol.draft_versions}
                  editMode={editMode}
                  onEditChange={setDraftEdits}
                  editContent={draftEdits}
                />
              </div>

              {/* Debate history */}
              {workflowHistory && workflowHistory.debate_history.length > 0 && (
                <DebateHistory debateHistory={workflowHistory.debate_history} />
              )}
            </div>

            {/* Right column - Status and controls */}
            <div className="space-y-6">
              {/* Agent status */}
              <AgentStatus
                activeAgent={currentProtocol.active_agent}
                approvalStatus={currentProtocol.approval_status}
                iterationCount={currentProtocol.iteration_count}
                maxIterations={currentProtocol.max_iterations}
              />

              {/* Quality scores */}
              <QualityScores
                safetyScore={currentProtocol.safety_score}
                clinicalScore={currentProtocol.clinical_score}
                empathyScores={currentProtocol.empathy_scores}
                safetyFlags={currentProtocol.safety_flags}
              />

              {/* Human review panel */}
              <HumanReviewPanel
                approvalStatus={currentProtocol.approval_status}
                safetyScore={currentProtocol.safety_score}
                clinicalScore={currentProtocol.clinical_score}
                empathyOverall={currentProtocol.empathy_scores.overall}
                onApprove={handleApprove}
                onReject={handleReject}
                editMode={editMode}
                onEditModeChange={setEditMode}
                feedback={humanFeedback}
                onFeedbackChange={setHumanFeedback}
                draftEdits={draftEdits}
                onDraftEditsChange={setDraftEdits}
                currentDraft={currentProtocol.current_draft || ''}
                isLoading={isApproving}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          Cerina Protocol Foundry • Multi-Agent Autonomous CBT System
        </div>
      </footer>
    </div>
  );
}
