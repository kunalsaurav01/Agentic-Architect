import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  FileText,
  History,
  Eye,
  Edit3,
  ChevronDown,
  ChevronUp,
  Clock,
} from 'lucide-react';
import { cn } from '../utils/cn';
import type { DraftVersion } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface ProtocolViewerProps {
  currentDraft: string;
  draftVersions: DraftVersion[];
  editMode: boolean;
  onEditChange?: (content: string) => void;
  editContent?: string;
}

export function ProtocolViewer({
  currentDraft,
  draftVersions,
  editMode,
  onEditChange,
  editContent,
}: ProtocolViewerProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  const displayContent = editMode
    ? editContent ?? currentDraft
    : selectedVersion !== null
    ? draftVersions.find((v) => v.version === selectedVersion)?.content || currentDraft
    : currentDraft;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-cerina-600" />
          <h3 className="text-lg font-semibold text-gray-900">Protocol Draft</h3>
          {draftVersions.length > 0 && (
            <span className="text-sm text-gray-500">
              v{selectedVersion ?? draftVersions.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editMode && (
            <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">
              <Edit3 className="w-4 h-4" />
              Edit Mode
            </div>
          )}
          {draftVersions.length > 1 && (
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={cn(
                'flex items-center gap-1 px-3 py-1.5 rounded text-sm transition-colors',
                showHistory
                  ? 'bg-gray-200 text-gray-900'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              <History className="w-4 h-4" />
              History
              {showHistory ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Version history panel */}
      {showHistory && (
        <div className="border-b border-gray-200 bg-gray-50 p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            Version History
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {[...draftVersions].reverse().map((version) => (
              <button
                key={version.version}
                onClick={() =>
                  setSelectedVersion(
                    selectedVersion === version.version ? null : version.version
                  )
                }
                className={cn(
                  'w-full flex items-start gap-3 p-2 rounded text-left transition-colors',
                  selectedVersion === version.version
                    ? 'bg-cerina-100 border border-cerina-300'
                    : 'hover:bg-gray-100'
                )}
              >
                <div
                  className={cn(
                    'px-2 py-0.5 rounded text-xs font-medium',
                    version.agent === 'human'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-blue-100 text-blue-700'
                  )}
                >
                  v{version.version}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 capitalize">
                      {version.agent.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(version.timestamp), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                  {version.changes_summary && (
                    <p className="text-xs text-gray-500 truncate mt-0.5">
                      {version.changes_summary}
                    </p>
                  )}
                </div>
                {selectedVersion === version.version ? (
                  <Eye className="w-4 h-4 text-cerina-600 flex-shrink-0" />
                ) : null}
              </button>
            ))}
          </div>
          {selectedVersion !== null && (
            <button
              onClick={() => setSelectedVersion(null)}
              className="mt-2 text-sm text-cerina-600 hover:text-cerina-700"
            >
              ← Back to current version
            </button>
          )}
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 overflow-auto p-4">
        {editMode ? (
          <textarea
            value={editContent ?? currentDraft}
            onChange={(e) => onEditChange?.(e.target.value)}
            className="w-full h-full min-h-[400px] p-4 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:ring-2 focus:ring-cerina-500 focus:border-cerina-500"
            placeholder="Edit the protocol here..."
          />
        ) : displayContent ? (
          <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-li:text-gray-700">
            <ReactMarkdown>{displayContent}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <FileText className="w-12 h-12 mb-2" />
            <p>No draft available yet</p>
            <p className="text-sm">The agents are working on your protocol...</p>
          </div>
        )}
      </div>

      {/* Footer with word count */}
      {displayContent && (
        <div className="p-2 border-t border-gray-200 text-xs text-gray-500 flex justify-between">
          <span>
            {displayContent.split(/\s+/).filter(Boolean).length} words
          </span>
          <span>{displayContent.length} characters</span>
        </div>
      )}
    </div>
  );
}
