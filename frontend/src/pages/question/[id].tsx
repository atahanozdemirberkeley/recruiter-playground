import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import Head from 'next/head';

interface QuestionPageProps {
  // Add any props you might need
}

export default function QuestionPage(props: QuestionPageProps) {
  const router = useRouter();
  const { id, title } = router.query;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!router.isReady) return;
    
    async function loadQuestion() {
      try {
        setLoading(true);
        
        // Example of how to make a request to your backend API
        // Replace this with your actual API endpoint
        const response = await fetch(`/api/questions/${id}`);
        
        if (!response.ok) {
          throw new Error('Failed to load question data');
        }
        
        const data = await response.json();
        console.log('Question data loaded:', data);
        
        // Here you would typically set question data to state
        // setQuestionData(data);
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading question:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    }
    
    loadQuestion();
  }, [router.isReady, id]);

  // Handle loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black text-white">
        <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-8 max-w-md">
          <h2 className="text-xl font-semibold mb-4">Error Loading Question</h2>
          <p>{error}</p>
          <button 
            onClick={() => router.back()}
            className="mt-4 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>{title ? `${title} | Coding Challenge` : 'Coding Challenge'}</title>
      </Head>
      
      <main className="min-h-screen bg-black text-white">
        <div className="container mx-auto py-8">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-bold">{title}</h1>
            <button 
              onClick={() => router.back()}
              className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700 transition-colors"
            >
              Back
            </button>
          </div>
          
          {/* This is where you would render your playground component */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <p className="text-lg mb-4">
              Question ID: {id}
            </p>
            
            {/* Replace this with your actual playground component */}
            <div className="bg-gray-800 p-4 rounded-md">
              <p className="text-gray-300 mb-2">This is where your coding playground would go.</p>
              <p className="text-gray-400">The data for this question has been loaded and is ready for use.</p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
} 