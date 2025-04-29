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
  };
}

const TestResults: React.FC<TestResultsProps> = ({ results }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
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
      <div className="bg-gray-100 dark:bg-gray-800 rounded-md p-4">
        <p className="text-gray-700 dark:text-gray-300">No test results available.</p>
      </div>
    );
  }

  const { test_results, summary } = results.results;

  return (
    <div className="bg-gray-100 dark:bg-gray-800 rounded-md">
      <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
        <Tab.List className="flex border-b border-gray-200 dark:border-gray-700">
          {test_results.map((_, index) => (
            <Tab
              key={index}
              className={({ selected }: { selected: boolean }) =>
                clsx(
                  'py-2 px-4 text-sm font-medium outline-none',
                  selected
                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                )
              }
            >
              Case {index + 1}
            </Tab>
          ))}
          <div className="ml-auto flex items-center pr-4">
            <span className={clsx(
              'px-2 py-1 rounded text-xs font-medium',
              summary.failed > 0
                ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
                : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
            )}>
              {summary.passed}/{summary.total} Passed
            </span>
          </div>
        </Tab.List>

        <Tab.Panels className="p-4">
          {test_results.map((testCase, index) => (
            <Tab.Panel key={index}>
              <div className="space-y-4">
                {testCase.inputs.map((input, inputIndex) => (
                  <div key={inputIndex} className="bg-white dark:bg-gray-900 p-3 rounded-md">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Input {inputIndex + 1}</div>
                    <div className="font-mono text-sm">{input}</div>
                  </div>
                ))}
                
                <div className="bg-white dark:bg-gray-900 p-3 rounded-md">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Expected</div>
                  <div className="font-mono text-sm">{JSON.stringify(testCase.expected)}</div>
                </div>
                
                <div className="bg-white dark:bg-gray-900 p-3 rounded-md">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Actual</div>
                  <div className={clsx(
                    'font-mono text-sm',
                    testCase.success
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  )}>
                    {JSON.stringify(testCase.actual)}
                  </div>
                </div>
                
                {testCase.error && (
                  <div className="bg-red-50 dark:bg-red-900 p-3 rounded-md">
                    <div className="text-xs text-red-500 dark:text-red-400 mb-1">Error</div>
                    <div className="font-mono text-sm text-red-600 dark:text-red-400">{testCase.error}</div>
                  </div>
                )}
                
                <div className={clsx(
                  'text-sm font-medium rounded-md p-2 text-center',
                  testCase.success
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
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