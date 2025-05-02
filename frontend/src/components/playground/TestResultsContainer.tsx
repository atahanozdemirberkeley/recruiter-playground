import React, { useState, useEffect } from 'react';
import TestResults from './TestResults';
import { useConnectionState, useLocalParticipant } from '@livekit/components-react';
import { ConnectionState } from 'livekit-client';

interface TestResultsContainerProps {
  // If needed, props for configuring room/participant connections can be added here
  roomName?: string;
}

const TestResultsContainer: React.FC<TestResultsContainerProps> = ({ roomName }) => {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const { localParticipant } = useLocalParticipant();
  const connectionState = useConnectionState();
  const isConnected = localParticipant && connectionState === ConnectionState.Connected;

  // Listen for test results from the backend
  useEffect(() => {
    // This is a placeholder for the actual implementation
    // You would use your LiveKit or WebSocket connection here to listen for test results
    
    const handleTestResults = (event: any) => {
      try {
        // Example of handling data from backend
        if (event.type === 'test_results') {
          setResults(event.data);
          setLoading(false);
        }
      } catch (error) {
        console.error('Error handling test results:', error);
      }
    };

    // Set up listener for test results
    // This is a placeholder - replace with your actual event listener
    // Example: window.addEventListener('test-results', handleTestResults);
    
    return () => {
      // Clean up listener
      // Example: window.removeEventListener('test-results', handleTestResults);
    };
  }, [roomName]);

  // For development/testing purposes - replace with real data in production
  useEffect(() => {
    // Example test results for development (can be removed in production)
    const exampleResults = {
      success: true,
      results: {
        test_results: [
          {
            test_id: 'f8a63e19-fc55-46b4-b8b2-2191db808628',
            inputs: ['{[]}'],
            expected: true,
            actual: true,
            success: true,
            error: null,
            time: 0.00003099
          },
          {
            test_id: '9828ad20-f908-44a5-9c45-7be6ad9b3cad',
            inputs: ['([{}])'],
            expected: true,
            actual: false,
            success: false,
            error: null,
            time: 0.00000
          },
          {
            test_id: 'ee03ee47-bbc2-4c75-a416-1f3bb3c94f91',
            inputs: ['((()))'],
            expected: true,
            actual: true,
            success: true,
            error: null,
            time: 0.00000
          }
        ],
        summary: {
          total: 3,
          passed: 2,
          failed: 1,
          execution_time: 0.00003099
        }
      },
      mode: 'run'
    };
    
    // Set example results after a short delay to simulate loading
    setTimeout(() => {
      setResults(exampleResults);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <div className="bg-gray-100 dark:bg-gray-800 rounded-md p-4 flex justify-center items-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="bg-gray-100 dark:bg-gray-800 rounded-md p-4">
        <p className="text-gray-700 dark:text-gray-300">Run your code to see test results.</p>
      </div>
    );
  }

  return <TestResults results={results} />;
};

export default TestResultsContainer; 