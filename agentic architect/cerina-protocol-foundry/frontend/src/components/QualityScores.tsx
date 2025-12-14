import React from 'react';
import { Shield, Brain, Heart, AlertTriangle, CheckCircle } from 'lucide-react';
import { cn } from '../utils/cn';
import type { EmpathyScores, SafetyFlag } from '../types';

interface QualityScoresProps {
  safetyScore: number;
  clinicalScore: number;
  empathyScores: EmpathyScores;
  safetyFlags: SafetyFlag[];
}

interface ScoreBarProps {
  label: string;
  score: number;
  icon: React.ReactNode;
  colorClass: string;
  threshold?: number;
}

function ScoreBar({ label, score, icon, colorClass, threshold = 7 }: ScoreBarProps) {
  const percentage = (score / 10) * 100;
  const isAboveThreshold = score >= threshold;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={colorClass}>{icon}</span>
          <span className="text-sm font-medium text-gray-700">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('text-sm font-bold', colorClass)}>
            {score.toFixed(1)}
          </span>
          <span className="text-xs text-gray-400">/10</span>
          {isAboveThreshold ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          )}
        </div>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={cn(
            'h-2 rounded-full transition-all duration-500',
            isAboveThreshold ? 'bg-green-500' : 'bg-amber-500'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export function QualityScores({
  safetyScore,
  clinicalScore,
  empathyScores,
  safetyFlags,
}: QualityScoresProps) {
  const unresolvedFlags = safetyFlags.filter((f) => !f.resolved);
  const criticalFlags = unresolvedFlags.filter((f) => f.severity === 'critical');
  const highFlags = unresolvedFlags.filter((f) => f.severity === 'high');

  const overallScore = (safetyScore + clinicalScore + empathyScores.overall) / 3;
  const allThresholdsMet =
    safetyScore >= 7 && clinicalScore >= 6 && empathyScores.overall >= 6;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Quality Scores</h3>
        <div
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            allThresholdsMet
              ? 'bg-green-100 text-green-700'
              : 'bg-amber-100 text-amber-700'
          )}
        >
          {allThresholdsMet ? 'Ready for Review' : 'Needs Improvement'}
        </div>
      </div>

      {/* Overall score circle */}
      <div className="flex justify-center mb-6">
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-gray-200"
            />
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${(overallScore / 10) * 251.2} 251.2`}
              className={cn(
                'transition-all duration-1000',
                overallScore >= 7
                  ? 'text-green-500'
                  : overallScore >= 5
                  ? 'text-amber-500'
                  : 'text-red-500'
              )}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-gray-900">
              {overallScore.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500">Overall</span>
          </div>
        </div>
      </div>

      {/* Individual scores */}
      <div className="space-y-4">
        <ScoreBar
          label="Safety"
          score={safetyScore}
          icon={<Shield className="w-4 h-4" />}
          colorClass="text-red-500"
          threshold={7}
        />
        <ScoreBar
          label="Clinical"
          score={clinicalScore}
          icon={<Brain className="w-4 h-4" />}
          colorClass="text-amber-500"
          threshold={6}
        />
        <ScoreBar
          label="Empathy"
          score={empathyScores.overall}
          icon={<Heart className="w-4 h-4" />}
          colorClass="text-pink-500"
          threshold={6}
        />
      </div>

      {/* Empathy breakdown */}
      {empathyScores.overall > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Empathy Breakdown
          </h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Warmth</span>
              <span className="font-medium">{empathyScores.warmth.toFixed(1)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Accessibility</span>
              <span className="font-medium">
                {empathyScores.accessibility.toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Safety Language</span>
              <span className="font-medium">
                {empathyScores.safety_language.toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Cultural</span>
              <span className="font-medium">
                {empathyScores.cultural_sensitivity.toFixed(1)}
              </span>
            </div>
          </div>
          {empathyScores.readability_grade && (
            <div className="mt-2 text-xs text-gray-500">
              Reading Level: {empathyScores.readability_grade}
            </div>
          )}
        </div>
      )}

      {/* Safety flags */}
      {unresolvedFlags.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Safety Flags ({unresolvedFlags.length})
          </h4>
          <div className="space-y-2">
            {unresolvedFlags.slice(0, 3).map((flag) => (
              <div
                key={flag.id}
                className={cn(
                  'p-2 rounded text-xs',
                  flag.severity === 'critical'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : flag.severity === 'high'
                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                    : 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                )}
              >
                <div className="font-medium uppercase">
                  [{flag.severity}] {flag.flag_type.replace(/_/g, ' ')}
                </div>
                <div className="mt-1 text-xs opacity-80">{flag.details}</div>
              </div>
            ))}
            {unresolvedFlags.length > 3 && (
              <div className="text-xs text-gray-500">
                +{unresolvedFlags.length - 3} more flags
              </div>
            )}
          </div>
        </div>
      )}

      {/* Threshold legend */}
      <div className="mt-4 pt-4 border-t border-gray-100 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-green-500" />
            <span>Above threshold</span>
          </div>
          <div className="flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-500" />
            <span>Below threshold</span>
          </div>
        </div>
      </div>
    </div>
  );
}
