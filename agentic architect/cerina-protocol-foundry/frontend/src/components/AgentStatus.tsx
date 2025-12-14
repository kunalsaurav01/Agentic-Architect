import React from 'react';
import {
  Brain,
  Shield,
  Heart,
  FileText,
  Users,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { cn } from '../utils/cn';
import type { AgentName, ApprovalStatus } from '../types';

interface AgentStatusProps {
  activeAgent: AgentName;
  approvalStatus: ApprovalStatus;
  iterationCount: number;
  maxIterations: number;
}

const agentConfig: Record<
  AgentName,
  { name: string; icon: React.ReactNode; color: string; description: string }
> = {
  supervisor: {
    name: 'Supervisor',
    icon: <Users className="w-5 h-5" />,
    color: 'text-purple-500',
    description: 'Coordinating agents and making routing decisions',
  },
  drafting: {
    name: 'Drafting Agent',
    icon: <FileText className="w-5 h-5" />,
    color: 'text-blue-500',
    description: 'Creating and refining the CBT protocol',
  },
  clinical_critic: {
    name: 'Clinical Critic',
    icon: <Brain className="w-5 h-5" />,
    color: 'text-amber-500',
    description: 'Evaluating therapeutic validity and structure',
  },
  safety_guardian: {
    name: 'Safety Guardian',
    icon: <Shield className="w-5 h-5" />,
    color: 'text-red-500',
    description: 'Checking for safety concerns and ethical issues',
  },
  empathy: {
    name: 'Empathy Agent',
    icon: <Heart className="w-5 h-5" />,
    color: 'text-pink-500',
    description: 'Enhancing warmth and accessibility',
  },
  human_review: {
    name: 'Human Review',
    icon: <Users className="w-5 h-5" />,
    color: 'text-green-500',
    description: 'Awaiting human approval',
  },
};

const allAgents: AgentName[] = [
  'supervisor',
  'drafting',
  'clinical_critic',
  'safety_guardian',
  'empathy',
  'human_review',
];

export function AgentStatus({
  activeAgent,
  approvalStatus,
  iterationCount,
  maxIterations,
}: AgentStatusProps) {
  const isComplete =
    approvalStatus === 'approved' || approvalStatus === 'rejected';
  const isPendingReview = approvalStatus === 'pending_human_review';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Agent Status</h3>
        <div className="text-sm text-gray-500">
          Iteration {iterationCount} / {maxIterations}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
        <div
          className={cn(
            'h-2 rounded-full transition-all duration-500',
            isComplete ? 'bg-green-500' : isPendingReview ? 'bg-amber-500' : 'bg-blue-500'
          )}
          style={{
            width: `${isComplete ? 100 : (iterationCount / maxIterations) * 100}%`,
          }}
        />
      </div>

      {/* Agent list */}
      <div className="space-y-3">
        {allAgents.map((agent) => {
          const config = agentConfig[agent];
          const isActive = activeAgent === agent;
          const isHumanReview = agent === 'human_review';

          // Determine if this agent should be highlighted
          const shouldHighlight =
            (isHumanReview && isPendingReview) || (!isHumanReview && isActive);

          return (
            <div
              key={agent}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
                shouldHighlight
                  ? 'bg-gray-100 border border-gray-300'
                  : 'opacity-50'
              )}
            >
              {/* Agent icon */}
              <div
                className={cn(
                  'p-2 rounded-full',
                  shouldHighlight ? config.color : 'text-gray-400',
                  shouldHighlight ? 'bg-white shadow-sm' : ''
                )}
              >
                {config.icon}
              </div>

              {/* Agent info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'font-medium',
                      shouldHighlight ? 'text-gray-900' : 'text-gray-500'
                    )}
                  >
                    {config.name}
                  </span>
                  {shouldHighlight && !isComplete && (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  )}
                </div>
                {shouldHighlight && (
                  <p className="text-sm text-gray-500 truncate">
                    {config.description}
                  </p>
                )}
              </div>

              {/* Status indicator */}
              <div>
                {isComplete && agent !== 'human_review' ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : isPendingReview && agent === 'human_review' ? (
                  <AlertCircle className="w-5 h-5 text-amber-500" />
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {/* Status message */}
      <div
        className={cn(
          'mt-4 p-3 rounded-lg text-sm',
          isComplete
            ? 'bg-green-50 text-green-700'
            : isPendingReview
            ? 'bg-amber-50 text-amber-700'
            : 'bg-blue-50 text-blue-700'
        )}
      >
        {isComplete ? (
          approvalStatus === 'approved' ? (
            <>
              <CheckCircle className="w-4 h-4 inline mr-2" />
              Protocol approved and finalized
            </>
          ) : (
            <>
              <AlertCircle className="w-4 h-4 inline mr-2" />
              Protocol rejected
            </>
          )
        ) : isPendingReview ? (
          <>
            <AlertCircle className="w-4 h-4 inline mr-2" />
            Protocol ready for human review. Please review and approve or request
            changes.
          </>
        ) : (
          <>
            <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
            Agents are working on your protocol...
          </>
        )}
      </div>
    </div>
  );
}
