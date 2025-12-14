import React, { useState } from 'react';
import {
  MessageCircle,
  ChevronDown,
  ChevronUp,
  Brain,
  Shield,
  Heart,
  FileText,
  Users,
} from 'lucide-react';
import { cn } from '../utils/cn';
import type { DebateEntry, AgentName } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface DebateHistoryProps {
  debateHistory: DebateEntry[];
  maxVisible?: number;
}

const agentIcons: Record<string, React.ReactNode> = {
  supervisor: <Users className="w-4 h-4" />,
  drafting: <FileText className="w-4 h-4" />,
  clinical_critic: <Brain className="w-4 h-4" />,
  safety_guardian: <Shield className="w-4 h-4" />,
  empathy: <Heart className="w-4 h-4" />,
};

const agentColors: Record<string, string> = {
  supervisor: 'bg-purple-100 text-purple-700 border-purple-200',
  drafting: 'bg-blue-100 text-blue-700 border-blue-200',
  clinical_critic: 'bg-amber-100 text-amber-700 border-amber-200',
  safety_guardian: 'bg-red-100 text-red-700 border-red-200',
  empathy: 'bg-pink-100 text-pink-700 border-pink-200',
};

const messageTypeStyles: Record<string, string> = {
  critique: 'border-l-amber-500',
  suggestion: 'border-l-blue-500',
  agreement: 'border-l-green-500',
  disagreement: 'border-l-red-500',
  question: 'border-l-purple-500',
};

export function DebateHistory({
  debateHistory,
  maxVisible = 5,
}: DebateHistoryProps) {
  const [expanded, setExpanded] = useState(false);

  if (debateHistory.length === 0) {
    return null;
  }

  const sortedHistory = [...debateHistory].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  const visibleHistory = expanded
    ? sortedHistory
    : sortedHistory.slice(0, maxVisible);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-cerina-600" />
          Agent Debate History
        </h3>
        <span className="text-sm text-gray-500">
          {debateHistory.length} message{debateHistory.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-3">
        {visibleHistory.map((entry, index) => (
          <div
            key={`${entry.timestamp}-${index}`}
            className={cn(
              'p-3 rounded-lg border-l-4 bg-gray-50',
              messageTypeStyles[entry.message_type] || 'border-l-gray-300'
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border',
                    agentColors[entry.from_agent] || 'bg-gray-100 text-gray-700'
                  )}
                >
                  {agentIcons[entry.from_agent]}
                  {entry.from_agent.replace(/_/g, ' ')}
                </span>
                {entry.to_agent && (
                  <>
                    <span className="text-gray-400">→</span>
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border',
                        agentColors[entry.to_agent] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {agentIcons[entry.to_agent]}
                      {entry.to_agent.replace(/_/g, ' ')}
                    </span>
                  </>
                )}
                <span
                  className={cn(
                    'px-1.5 py-0.5 rounded text-xs',
                    entry.message_type === 'critique'
                      ? 'bg-amber-100 text-amber-600'
                      : entry.message_type === 'suggestion'
                      ? 'bg-blue-100 text-blue-600'
                      : entry.message_type === 'agreement'
                      ? 'bg-green-100 text-green-600'
                      : entry.message_type === 'disagreement'
                      ? 'bg-red-100 text-red-600'
                      : 'bg-gray-100 text-gray-600'
                  )}
                >
                  {entry.message_type}
                </span>
              </div>
              <div className="text-xs text-gray-400 flex-shrink-0">
                iter {entry.iteration + 1} •{' '}
                {formatDistanceToNow(new Date(entry.timestamp), {
                  addSuffix: true,
                })}
              </div>
            </div>
            <p className="mt-2 text-sm text-gray-700">{entry.message}</p>
          </div>
        ))}
      </div>

      {debateHistory.length > maxVisible && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 w-full flex items-center justify-center gap-1 py-2 text-sm text-cerina-600 hover:text-cerina-700 hover:bg-gray-50 rounded"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show {debateHistory.length - maxVisible} more
            </>
          )}
        </button>
      )}
    </div>
  );
}
