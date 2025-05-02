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
  };
}

const TestResults: React.FC<TestResultsProps> = ({ results }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  // Determine if we're in submit or run state
  const isSubmitState = results.state === 'submit';
  
  // Handle error case
  if (!results.success && results.error) {
    return (
      <div className="bg-gray-900 rounded-md p-4 text-red-400 font-mono text-sm">
        <div className="font-bold mb-2">Error:</div>
        <div>{results.error}</div>
      </div>
    );
  }

  // Handle empty or invalid results
  if (!results.results || !results.results.test_results || results.results.test_results.length === 0) {
    return (
      <div className="bg-gray-900 rounded-md p-4">
        <p className="text-gray-300">No test results available.</p>
      </div>
    );
  }

  const { test_results, summary } = results.results;

  // Submit state - only show summary
  if (isSubmitState) {
    return (
      <div className="bg-gray-900 rounded-md p-6">
        <div className="flex flex-col items-center justify-center">
          <div className={clsx(
            'text-xl font-bold mb-2',
            summary.failed > 0 ? 'text-red-400' : 'text-green-400'
          )}>
            {summary.passed === summary.total 
              ? 'All Tests Passed!' 
              : `${summary.passed}/${summary.total} Tests Passed`
            }
          </div>
          
          <div className={clsx(
            'mt-2 py-2 px-4 rounded-md',
            summary.failed > 0
              ? 'bg-red-900 text-red-300'
              : 'bg-green-900 text-green-300'
          )}>
            {summary.failed > 0 
              ? 'Your submission did not pass all tests.' 
              : 'Your submission passed all tests!'
            }
          </div>
          
          <div className="text-sm text-gray-400 mt-4">
            Execution time: {summary.execution_time.toFixed(6)}s
          </div>
        </div>
      </div>
    );
  }

  // Run state - show detailed test cases
  return (
    <div className="bg-gray-900 rounded-md">
      <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
        <Tab.List className="flex border-b border-gray-700">
          {test_results.map((testCase, index) => (
            <Tab
              key={index}
              className={({ selected }: { selected: boolean }) =>
                clsx(
                  'py-2 px-4 text-sm font-medium outline-none',
                  selected
                    ? testCase.success 
                      ? 'border-b-2 border-green-500 text-green-400' 
                      : 'border-b-2 border-red-500 text-red-400'
                    : testCase.success
                      ? 'text-green-400 hover:text-green-300'
                      : 'text-red-400 hover:text-red-300'
                )
              }
            >
              Case {index + 1}
            </Tab>
          ))}
          <div className="ml-auto flex items-center pr-4">
            <span className={clsx(
              'px-2 py-1 rounded text-xs font-medium flex items-center',
              summary.failed > 0
                ? 'bg-red-900 text-red-300'
                : 'bg-green-900 text-green-300'
            )}>
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
                  <div key={inputIndex} className="bg-gray-800 p-3 rounded-md">
                    <div className="text-xs text-gray-400 mb-1">Input {inputIndex + 1}</div>
                    <div className="font-mono text-sm text-gray-200">{input}</div>
                  </div>
                ))}
                
                <div className="bg-gray-800 p-3 rounded-md">
                  <div className="text-xs text-gray-400 mb-1">Expected</div>
                  <div className="font-mono text-sm text-gray-200">{JSON.stringify(testCase.expected)}</div>
                </div>
                
                <div className="bg-gray-800 p-3 rounded-md">
                  <div className="text-xs text-gray-400 mb-1">Actual</div>
                  <div className={clsx(
                    'font-mono text-sm',
                    testCase.success
                      ? 'text-green-400'
                      : 'text-red-400'
                  )}>
                    {JSON.stringify(testCase.actual)}
                  </div>
                </div>
                
                {testCase.error && (
                  <div className="bg-red-900 p-3 rounded-md">
                    <div className="text-xs text-red-400 mb-1">Error</div>
                    <div className="font-mono text-sm text-red-400">{testCase.error}</div>
                  </div>
                )}
                
                <div className={clsx(
                  'text-sm font-medium rounded-md p-2 text-center',
                  testCase.success
                    ? 'bg-green-900 text-green-300'
                    : 'bg-red-900 text-red-300'
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