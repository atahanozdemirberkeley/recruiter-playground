import React, { useState } from 'react';
import { Tab } from '@headlessui/react';
import clsx from 'clsx';

interface TestCase {
  test_id: string;
  inputs: string[];
  expected: any;
  actual: any;
  success: boolean;
  error: string | null;
  time: number;
}

interface TestSummary {
  total: number;
  passed: number;
  failed: number;
  execution_time: number;
}

interface TestResults {
  test_results: TestCase[];
  summary: TestSummary;
}

interface TestResultsProps {
  results: {
    success: boolean;
    results?: TestResults;
    error?: string;
    mode: string;
    state: 'run' | 'submit';
    cooldown?: boolean;
    time_remaining?: number;
  };
}

const TestResults: React.FC<TestResultsProps> = ({ results }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  // Determine if we're in submit or run state
  const isSubmitState = results.state === 'submit';
  
  // Handle cooldown case
  if (!results.success && results.cooldown) {
    return (
      <div className="glass-panel rounded-lg p-4 text-white">
        <div className="flex flex-col items-center justify-center">
          <div className="text-amber-300 font-medium mb-2">Execution Cooldown</div>
          <div className="bg-amber-500/30 text-amber-300 py-2 px-4 rounded-lg text-center border border-amber-500/20 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
            {results.error || `Please wait before running code again in ${results.mode} mode.`}
          </div>
        </div>
      </div>  
    );
  }
  
  // Handle error case
  if (!results.success && results.error) {
    return (
      <div className="glass-panel rounded-lg p-4 text-red-300 font-mono text-sm">
        <div className="font-medium mb-2">Error:</div>
        <div className="bg-red-500/20 p-3 rounded-lg border border-red-500/30 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">{results.error}</div>
      </div>
    );
  }

  // Handle empty or invalid results
  if (!results.results || !results.results.test_results || results.results.test_results.length === 0) {
    return (
      <div className="glass-panel rounded-lg p-4">
        <p className="text-amber-300">No test results available.</p>
      </div>
    );
  }

  const { test_results, summary } = results.results;

  // Submit state - only show summary
  if (isSubmitState) {
    return (
      <div className="glass-panel rounded-lg p-6 backdrop-blur-sm">
        <div className="flex flex-col items-center justify-center">
          <div className={clsx(
            'header-gradient text-xl font-bold mb-4',
            summary.failed > 0 ? 'from-red-300 to-red-500' : 'from-green-300 to-green-500'
          )}>
            {summary.passed === summary.total 
              ? 'All Tests Passed!' 
              : `${summary.passed}/${summary.total} Tests Passed`
            }
          </div>
          
          <div className={clsx(
            'mt-2 py-2 px-6 rounded-lg backdrop-blur-sm transform perspective-hover transition-all duration-300',
            summary.failed > 0
              ? 'bg-red-500/30 text-red-300 border border-red-500/30'
              : 'bg-green-500/30 text-green-300 border border-green-500/30'
          )}>
            {summary.failed > 0 
              ? 'Your submission did not pass all tests.' 
              : 'Your submission passed all tests!'
            }
          </div>
        </div>
      </div>
    );
  }

  // Run state - show detailed test cases
  return (
    <div className="glass-panel rounded-lg backdrop-blur-sm">
      <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
        <Tab.List className="flex border-b border-gray-700/40">
          {test_results.map((testCase, index) => (
            <Tab
              key={index}
              className={({ selected }: { selected: boolean }) =>
                clsx(
                  'py-2 px-4 text-sm font-medium outline-none transition-all duration-200',
                  selected
                    ? testCase.success 
                      ? 'border-b-2 border-green-500 text-green-300 bg-green-500/10' 
                      : 'border-b-2 border-red-500 text-red-300 bg-red-500/10'
                    : testCase.success
                      ? 'text-green-400 hover:text-green-300 hover:bg-green-500/5'
                      : 'text-red-400 hover:text-red-300 hover:bg-red-500/5'
                )
              }
            >
              Case {index + 1}
            </Tab>
          ))}
          <div className="ml-auto flex items-center pr-4">
            <span className={clsx(
              'px-3 py-1 rounded-lg text-xs font-medium flex items-center transform translate-z-4',
              summary.failed > 0
                ? 'bg-red-500/30 text-red-300 border border-red-500/30'
                : 'bg-green-500/30 text-green-300 border border-green-500/30'
            )}
            style={{transform: 'translateZ(4px)'}}>
              {summary.failed > 0 ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {summary.passed}/{summary.total} Passed
            </span>
          </div>
        </Tab.List>

        <Tab.Panels className="p-4">
          {test_results.map((testCase, index) => (
            <Tab.Panel key={index}>
              <div className="space-y-4">
                {testCase.inputs.map((input, inputIndex) => (
                  <div key={inputIndex} className="bg-recurit-blue/30 p-3 rounded-lg border border-recurit-blue/20 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                    <div className="text-xs text-gray-300 mb-1">Input {inputIndex + 1}</div>
                    <div className="font-mono text-sm text-gray-200">{input}</div>
                  </div>
                ))}
                
                <div className="bg-recurit-blue/30 p-3 rounded-lg border border-recurit-blue/20 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                  <div className="text-xs text-gray-300 mb-1">Expected</div>
                  <div className="font-mono text-sm text-gray-200">{JSON.stringify(testCase.expected)}</div>
                </div>
                
                <div className="bg-recurit-blue/30 p-3 rounded-lg border border-recurit-blue/20 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                  <div className="text-xs text-gray-300 mb-1">Actual</div>
                  <div className={clsx(
                    'font-mono text-sm',
                    testCase.success
                      ? 'text-green-300'
                      : 'text-red-300'
                  )}>
                    {JSON.stringify(testCase.actual)}
                  </div>
                </div>
                
                {testCase.error && (
                  <div className="bg-red-500/20 p-3 rounded-lg border border-red-500/30 backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                    <div className="text-xs text-red-300 mb-1">Error</div>
                    <div className="font-mono text-sm text-red-300">{testCase.error}</div>
                  </div>
                )}
                
                <div className={clsx(
                  'text-sm font-medium rounded-lg p-2 text-center backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]',
                  testCase.success
                    ? 'bg-green-500/30 text-green-300 border border-green-500/30'
                    : 'bg-red-500/30 text-red-300 border border-red-500/30'
                )}>
                  {testCase.success ? 'Test Passed' : 'Test Failed'}
                  <span className="text-xs ml-2 opacity-75">({testCase.time.toFixed(6)}s)</span>
                </div>
              </div>
            </Tab.Panel>
          ))}
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
};

export default TestResults; 