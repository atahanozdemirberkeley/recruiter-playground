import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
} from "@livekit/components-react";
import { AnimatePresence, motion } from "framer-motion";
import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from 'next/router';

import { PlaygroundConnect } from "src/components/PlaygroundConnect";
import Playground from "src/components/playground/Playground";
import {
  PlaygroundToast,
} from "src/components/toast/PlaygroundToast";
import { ConfigProvider, useConfig } from "src/hooks/useConfig";
import {
  ConnectionMode,
  ConnectionProvider,
  useConnection,
} from "src/hooks/useConnection";
import { ToastProvider, useToast } from "src/components/toast/ToasterProvider";

// Define colors for theme
const themeColors = [
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
  return (
    <ToastProvider>
      <ConfigProvider>
        <ConnectionProvider>
          <QuestionInner />
        </ConnectionProvider>
      </ConfigProvider>
    </ToastProvider>
  );
}

export function QuestionInner() {
  const router = useRouter();
  const { id, title } = router.query;
  const [questionInfo, setQuestionInfo] = useState<{ id: string; title: string } | null>(null);
  
  const { shouldConnect, wsUrl, token, mode, connect, disconnect } =
    useConnection();

  const { config } = useConfig();
  const { toastMessage, setToastMessage } = useToast();

  // Set question info from URL parameters
  useEffect(() => {
    if (router.isReady && id && title) {
      const questionData = {
        id: id as string,
        title: title as string
      };
      
      setQuestionInfo(questionData);
      
      // Store in localStorage for main.py to access
      localStorage.setItem('questionId', questionData.id);
      localStorage.setItem('questionTitle', questionData.title);
      
      // Log for debugging
      console.log('Question info from URL:', questionData);
    }
  }, [router.isReady, id, title]);

  const handleConnect = useCallback(
    async (c: boolean, mode: ConnectionMode) => {
      c ? connect(mode) : disconnect();
    },
    [connect, disconnect]
  );

  const showPG = useMemo(() => {
    if (process.env.NEXT_PUBLIC_LIVEKIT_URL) {
      return true;
    }
    if (wsUrl) {
      return true;
    }
    return false;
  }, [wsUrl]);

  // Handle loading state for question info
  if (!questionInfo && router.isReady && (id || title)) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>{questionInfo?.title ? `${questionInfo.title} | Coding Challenge` : config.title}</title>
        <meta name="description" content={config.description} />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"
        />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main className="relative flex flex-col justify-center px-4 items-center h-full w-full bg-black repeating-square-background">
        {questionInfo && (
          <div className="absolute top-0 left-0 p-4 z-10">
            <h1 className="text-xl font-semibold text-white">{questionInfo.title}</h1>
            <div className="text-gray-400 text-sm">Question ID: {questionInfo.id}</div>
          </div>
        )}
        <AnimatePresence>
          {toastMessage && (
            <motion.div
              className="left-0 right-0 top-0 absolute z-10"
              initial={{ opacity: 0, translateY: -50 }}
              animate={{ opacity: 1, translateY: 0 }}
              exit={{ opacity: 0, translateY: -50 }}
            >
              <PlaygroundToast />
            </motion.div>
          )}
        </AnimatePresence>
        {showPG ? (
          <LiveKitRoom
            className="flex flex-col h-full w-full"
            serverUrl={wsUrl}
            token={token}
            connect={shouldConnect}
            onError={(e) => {
              setToastMessage({ message: e.message, type: "error" });
              console.error(e);
            }}
          >
            <Playground
              themeColors={themeColors}
              onConnect={(c) => {
                const m = process.env.NEXT_PUBLIC_LIVEKIT_URL ? "env" : mode;
                handleConnect(c, m);
              }}
            />
            <RoomAudioRenderer />
            <StartAudio label="Click to enable audio playback" />
          </LiveKitRoom>
        ) : (
          <PlaygroundConnect
            accentColor={themeColors[0]}
            onConnectClicked={(mode) => {
              handleConnect(true, mode);
            }}
          />
        )}
      </main>
    </>
  );
} 