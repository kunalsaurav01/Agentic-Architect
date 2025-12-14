import React, { useState } from 'react';
import { Sparkles, Loader2, HelpCircle } from 'lucide-react';
import { cn } from '../utils/cn';

interface CreateProtocolFormProps {
  onSubmit: (userIntent: string, additionalContext?: string) => Promise<void>;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  'Create an exposure hierarchy for social anxiety disorder',
  'Design a sleep hygiene protocol for chronic insomnia',
  'Develop a behavioral activation plan for major depression',
  'Create a cognitive restructuring exercise for generalized anxiety',
  'Design a panic attack coping protocol with grounding techniques',
  'Create a thought record template for automatic negative thoughts',
  'Develop a progressive muscle relaxation protocol for stress',
  'Design an assertiveness training module for social skills',
];

export function CreateProtocolForm({ onSubmit, isLoading }: CreateProtocolFormProps) {
  const [userIntent, setUserIntent] = useState('');
  const [additionalContext, setAdditionalContext] = useState('');
  const [showContext, setShowContext] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userIntent.trim() || isLoading) return;
    await onSubmit(userIntent.trim(), additionalContext.trim() || undefined);
    setUserIntent('');
    setAdditionalContext('');
  };

  const useExample = (example: string) => {
    setUserIntent(example);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-6 h-6 text-cerina-600" />
        <h2 className="text-xl font-semibold text-gray-900">
          Create New CBT Protocol
        </h2>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Main input */}
        <div className="mb-4">
          <label
            htmlFor="userIntent"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            What CBT protocol would you like to create?
          </label>
          <textarea
            id="userIntent"
            value={userIntent}
            onChange={(e) => setUserIntent(e.target.value)}
            placeholder="e.g., Create an exposure hierarchy for agoraphobia"
            className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-cerina-500 focus:border-cerina-500"
            rows={3}
            disabled={isLoading}
          />
        </div>

        {/* Additional context (collapsible) */}
        <div className="mb-4">
          <button
            type="button"
            onClick={() => setShowContext(!showContext)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
          >
            <HelpCircle className="w-4 h-4" />
            {showContext ? 'Hide' : 'Add'} additional context
          </button>
          {showContext && (
            <textarea
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
              placeholder="Any specific requirements, target population details, or preferences..."
              className="mt-2 w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-cerina-500 focus:border-cerina-500"
              rows={2}
              disabled={isLoading}
            />
          )}
        </div>

        {/* Example prompts */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2">Try an example:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.slice(0, 4).map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => useExample(example)}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                disabled={isLoading}
              >
                {example.length > 40 ? example.slice(0, 40) + '...' : example}
              </button>
            ))}
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={!userIntent.trim() || isLoading}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-colors',
            !userIntent.trim() || isLoading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-cerina-600 text-white hover:bg-cerina-700'
          )}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Creating Protocol...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Create Protocol
            </>
          )}
        </button>
      </form>

      {/* Info text */}
      <p className="mt-4 text-xs text-gray-500">
        The multi-agent system will draft, critique, safety-check, and refine your
        protocol. You'll have the opportunity to review and approve before
        finalization.
      </p>
    </div>
  );
}
