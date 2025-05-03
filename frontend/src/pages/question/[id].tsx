import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import Head from 'next/head';
import Playground from 'src/components/playground/Playground';
import { ConnectionProvider, useConnection } from 'src/hooks/useConnection';
import { ToastProvider } from 'src/components/toast/ToasterProvider';

// Define colors for theme
const themeColors = [
  "recurit-accent", // Add the main recurit accent color first
  "cyan",
  "green",
  "amber",
  "blue",
  "violet",
  "rose",
  "pink",
  "teal",
];

export default function QuestionPage() {
  const router = useRouter();
  const { id, title } = router.query;
  const [questionInfo, setQuestionInfo] = useState<{ id: string; title: string } | null>(null);

  // Set question info from URL parameters
  useEffect(() => {
    if (router.isReady && id && title) {
      setQuestionInfo({
        id: id as string,
        title: title as string
      });
      
      // Log for debugging
      console.log('Question info from URL:', { id, title });
    }
  }, [router.isReady, id, title]);

  // Handle loading state
  if (!questionInfo) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-radial from-recurit-blue to-recurit-darker">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-recurit-accent"></div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>{questionInfo.title ? `${questionInfo.title} | Recurit Challenge` : 'Coding Challenge'}</title>
      </Head>
      
      <ToastProvider>
        <ConfigProvider>
          <ConnectionProvider>
            <PlaygroundWithConnection questionId={questionInfo.id} questionTitle={questionInfo.title} />
          </ConnectionProvider>
        </ConfigProvider>
      </ToastProvider>
    </>
  );
}

function PlaygroundWithConnection({ questionId, questionTitle }: { questionId: string, questionTitle: string }) {
  const { shouldConnect, wsUrl, token, mode, connect, disconnect } = useConnection();
  
  const handleConnect = async (c: boolean, opts?: { token: string; url: string }) => {
    if (c) {
      // When connecting, store question info in localStorage for main.py to access
      localStorage.setItem('questionId', questionId);
      localStorage.setItem('questionTitle', questionTitle);
      
      // Connect to the server
      connect(mode);
    } else {
      disconnect();
    }
  };

  return (
    <Playground
      themeColors={themeColors}
      onConnect={handleConnect}
    />
  );
}

// Add ConfigProvider if not imported automatically
function ConfigProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
} 