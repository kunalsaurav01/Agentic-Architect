import React, { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Edit3,
  MessageSquare,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '../utils/cn';
import type { ApprovalStatus } from '../types';

interface HumanReviewPanelProps {
  approvalStatus: ApprovalStatus;
  safetyScore: number;
  clinicalScore: number;
  empathyOverall: number;
  onApprove: (feedback?: string, edits?: string) => Promise<void>;
  onReject: (feedback: string, edits?: string) => Promise<void>;
  editMode: boolean;
  onEditModeChange: (editMode: boolean) => void;
  feedback: string;
  onFeedbackChange: (feedback: string) => void;
  draftEdits: string;
  onDraftEditsChange: (edits: string) => void;
  currentDraft: string;
  isLoading?: boolean;
}

export function HumanReviewPanel({
  approvalStatus,
  safetyScore,
  clinicalScore,
  empathyOverall,
  onApprove,
  onReject,
  editMode,
  onEditModeChange,
  feedback,
  onFeedbackChange,
  draftEdits,
  onDraftEditsChange,
  currentDraft,
  isLoading = false,
}: HumanReviewPanelProps) {
  const isPendingReview = approvalStatus === 'pending_human_review';
  const isApproved = approvalStatus === 'approved';
  const isRejected = approvalStatus === 'rejected';

  const allThresholdsMet =
    safetyScore >= 7 && clinicalScore >= 6 && empathyOverall >= 6;

  const handleApprove = async () => {
    await onApprove(feedback || undefined, editMode ? draftEdits : undefined);
  };

  const handleReject = async () => {
    if (!feedback.trim()) {
      alert('Please provide feedback for the revision.');
      return;
    }
    await onReject(feedback, editMode ? draftEdits : undefined);
  };

  const toggleEditMode = () => {
    if (!editMode) {
      onDraftEditsChange(currentDraft);
    }
    onEditModeChange(!editMode);
  };

  if (isApproved) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle className="w-5 h-5" />
          <span className="font-semibold">Protocol Approved</span>
        </div>
        <p className="mt-2 text-sm text-green-600">
          This protocol has been approved and finalized. It is now ready for use.
        </p>
      </div>
    );
  }

  if (isRejected) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-700">
          <XCircle className="w-5 h-5" />
          <span className="font-semibold">Protocol Rejected</span>
        </div>
        <p className="mt-2 text-sm text-red-600">
          This protocol was rejected and will not be used.
        </p>
      </div>
    );
  }

  if (!isPendingReview) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-700">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="font-semibold">Agents Working</span>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          The agents are still refining the protocol. Human review will be available
          once they've reached a satisfactory draft.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-cerina-600" />
          Human Review Required
        </h3>
        {!allThresholdsMet && (
          <div className="flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 rounded text-sm">
            <AlertTriangle className="w-4 h-4" />
            Thresholds not met
          </div>
        )}
      </div>

      {/* Quality summary */}
      <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div
            className={cn(
              'text-lg font-bold',
              safetyScore >= 7 ? 'text-green-600' : 'text-amber-600'
            )}
          >
            {safetyScore.toFixed(1)}
          </div>
          <div className="text-xs text-gray-500">Safety</div>
        </div>
        <div className="text-center">
          <div
            className={cn(
              'text-lg font-bold',
              clinicalScore >= 6 ? 'text-green-600' : 'text-amber-600'
            )}
          >
            {clinicalScore.toFixed(1)}
          </div>
          <div className="text-xs text-gray-500">Clinical</div>
        </div>
        <div className="text-center">
          <div
            className={cn(
              'text-lg font-bold',
              empathyOverall >= 6 ? 'text-green-600' : 'text-amber-600'
            )}
          >
            {empathyOverall.toFixed(1)}
          </div>
          <div className="text-xs text-gray-500">Empathy</div>
        </div>
      </div>

      {/* Edit mode toggle */}
      <div className="mb-4">
        <button
          onClick={toggleEditMode}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors w-full justify-center',
            editMode
              ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          )}
        >
          <Edit3 className="w-4 h-4" />
          {editMode ? 'Editing Protocol' : 'Click to Edit Protocol'}
        </button>
      </div>

      {/* Feedback textarea */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Feedback / Comments {!allThresholdsMet && '(recommended for approval)'}
        </label>
        <textarea
          value={feedback}
          onChange={(e) => onFeedbackChange(e.target.value)}
          placeholder="Provide feedback or comments for the protocol..."
          className="w-full p-3 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-cerina-500 focus:border-cerina-500"
          rows={3}
        />
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={isLoading}
          className={cn(
            'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors',
            isLoading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 text-white hover:bg-green-700'
          )}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <CheckCircle className="w-5 h-5" />
          )}
          Approve Protocol
        </button>
        <button
          onClick={handleReject}
          disabled={isLoading || !feedback.trim()}
          className={cn(
            'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors',
            isLoading || !feedback.trim()
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-amber-600 text-white hover:bg-amber-700'
          )}
          title={!feedback.trim() ? 'Please provide feedback for revision' : undefined}
        >
          <XCircle className="w-5 h-5" />
          Request Revision
        </button>
      </div>

      {/* Help text */}
      <p className="mt-3 text-xs text-gray-500">
        <strong>Approve:</strong> Finalize the protocol as-is (or with your edits).{' '}
        <strong>Request Revision:</strong> Send back to agents with feedback.
      </p>
    </div>
  );
}
