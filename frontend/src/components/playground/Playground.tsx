"use client";

import { LoadingSVG } from "src/components/button/LoadingSVG";
import { ChatMessageType } from "src/components/chat/ChatTile";
import { ColorPicker } from "src/components/colorPicker/ColorPicker";
import { AudioInputTile } from "src/components/config/AudioInputTile";
import { ConfigurationPanelItem } from "src/components/config/ConfigurationPanelItem";
import { NameValueRow } from "src/components/config/NameValueRow";
import { PlaygroundHeader } from "src/components/playground/PlaygroundHeader";
import {
  PlaygroundTab,
  PlaygroundTabbedTile,
  PlaygroundTile,
} from "src/components/playground/PlaygroundTile";
import { useConfig } from "src/hooks/useConfig";
import { TranscriptionTile } from "src/transcriptions/TranscriptionTile";
import {
  BarVisualizer,
  VideoTrack,
  useConnectionState,
  useDataChannel,
  useLocalParticipant,
  useRoomInfo,
  useTracks,
  useVoiceAssistant,
} from "@livekit/components-react";
import { ConnectionState, LocalParticipant, Track } from "livekit-client";
import { QRCodeSVG } from "qrcode.react";
import { ReactNode, useCallback, useEffect, useMemo, useState, useRef } from "react";
import tailwindTheme from "src/lib/tailwindTheme.preval";
import { InterviewTimer } from "src/components/timer/InterviewTimer";
import { Button } from "src/components/button/Button";
import { CodeEditor } from "../codeEditor/CodeEditor";

export interface PlaygroundMeta {
  name: string;
  value: string;
}

export interface PlaygroundProps {
  logo?: ReactNode;
  themeColors: string[];
  onConnect: (connect: boolean, opts?: { token: string; url: string }) => void;
}

const headerHeight = 56;

export default function Playground({
  logo,
  themeColors,
  onConnect,
}: PlaygroundProps) {
  const { config, setUserSettings } = useConfig();
  const { name } = useRoomInfo();
  const [transcripts, setTranscripts] = useState<ChatMessageType[]>([]);
  const [userCode, setUserCode] = useState<string>("");
  const [questionDescription, setQuestionDescription] = useState<string>("");
  const [descriptionHeight, setDescriptionHeight] = useState<number>(200);
  const { localParticipant } = useLocalParticipant();
  const resizingRef = useRef<boolean>(false);
  const startYRef = useRef<number>(0);
  const startHeightRef = useRef<number>(0);

  const voiceAssistant = useVoiceAssistant();

  const roomState = useConnectionState();
  const tracks = useTracks();

  useEffect(() => {
    if (roomState === ConnectionState.Connected) {
      localParticipant.setCameraEnabled(config.settings.inputs.camera);
      localParticipant.setMicrophoneEnabled(config.settings.inputs.mic);
    } else if (roomState === ConnectionState.Disconnected) {
      // Reset states when disconnected
      setUserCode("# Waiting for question...");
      setQuestionDescription("");
      setTranscripts([]);
    }
  }, [config, localParticipant, roomState, setUserCode, setQuestionDescription, setTranscripts]);

  const agentVideoTrack = tracks.find(
    (trackRef) =>
      trackRef.publication.kind === Track.Kind.Video &&
      trackRef.participant.isAgent
  );

  const localTracks = tracks.filter(
    ({ participant }) => participant instanceof LocalParticipant
  );
  const localVideoTrack = localTracks.find(
    ({ source }) => source === Track.Source.Camera
  );
  const localMicTrack = localTracks.find(
    ({ source }) => source === Track.Source.Microphone
  );

  const onDataReceived = useCallback(
    (msg: any) => {
      const decoded = JSON.parse(new TextDecoder("utf-8").decode(msg.payload));

      if (msg.topic === "transcription") {
        let timestamp = new Date().getTime();
        if ("timestamp" in decoded && decoded.timestamp > 0) {
          timestamp = decoded.timestamp;
        }
        setTranscripts([
          ...transcripts,
          {
            name: "You",
            message: decoded.text,
            timestamp: timestamp,
            isSelf: true,
          },
        ]);
      } else if (decoded.type === "question_data" && msg.topic === "question-data") {
        // Handle the question description and skeleton separately
        const { description, skeleton_code } = decoded.data;
        
        // Store description in separate state
        setQuestionDescription(description || "");
        
        // Create formatted code with only the skeleton code
        const formattedCode = `${skeleton_code || ''}`;
        
        // Set the code in the editor
        setUserCode(formattedCode);
      } else if (decoded.type === "test_results") {
        // Handle test results if needed
        console.log("Test results received:", decoded.data);
      }
    },
    [transcripts, setUserCode, setQuestionDescription]
  );

  useDataChannel(onDataReceived);

  const videoTileContent = useMemo(() => {
    const videoFitClassName = `object-${config.video_fit || "cover"}`;

    const disconnectedContent = (
      <div className="flex items-center justify-center text-gray-700 text-center w-full h-full">
        No video track. Connect to get started.
      </div>
    );

    const loadingContent = (
      <div className="flex flex-col items-center justify-center gap-2 text-gray-700 text-center h-full w-full">
        <LoadingSVG />
        Waiting for video track
      </div>
    );

    const videoContent = (
      <VideoTrack
        trackRef={agentVideoTrack}
        className={`absolute top-1/2 -translate-y-1/2 ${videoFitClassName} object-position-center w-full h-full`}
      />
    );

    let content = null;
    if (roomState === ConnectionState.Disconnected) {
      content = disconnectedContent;
    } else if (agentVideoTrack) {
      content = videoContent;
    } else {
      content = loadingContent;
    }

    return (
      <div className="flex flex-col w-full grow text-gray-950 bg-black rounded-sm border border-gray-800 relative">
        {content}
      </div>
    );
  }, [agentVideoTrack, config, roomState]);

  useEffect(() => {
    document.body.style.setProperty(
      "--lk-theme-color",
      // @ts-ignore
      tailwindTheme.colors[config.settings.theme_color]["500"]
    );
    document.body.style.setProperty(
      "--lk-drop-shadow",
      `var(--lk-theme-color) 0px 0px 18px`
    );
  }, [config.settings.theme_color]);

  const agentAudioVisualizer = useMemo(() => {
    if (!voiceAssistant.audioTrack) {
      if (roomState === ConnectionState.Disconnected) {
        return (
          <div className="flex flex-col items-center justify-center gap-2 text-gray-700 text-center w-full h-[100px]">
            No audio track. Connect to get started.
          </div>
        );
      } else {
        return (
          <div className="flex flex-col items-center gap-2 text-gray-700 text-center w-full h-[100px]">
            <LoadingSVG />
            Waiting for audio track
          </div>
        );
      }
    }

    return (
      <div
        className={`flex items-center justify-center w-full h-[100px] [--lk-va-bar-width:30px] [--lk-va-bar-gap:20px] [--lk-fg:var(--lk-theme-color)]`}
      >
        <BarVisualizer
          state={voiceAssistant.state}
          trackRef={voiceAssistant.audioTrack}
          barCount={5}
          options={{ minHeight: 20 }}
        />
      </div>
    );
  }, [
    voiceAssistant.audioTrack,
    voiceAssistant.state,
    roomState
  ]);

  const chatTileContent = useMemo(() => {
    if (voiceAssistant.audioTrack) {
      return (
        <>
          <TranscriptionTile
            agentAudioTrack={voiceAssistant.audioTrack}
            accentColor={config.settings.theme_color}
          />
        </>
      );
    }
    return <></>;
  }, [config.settings.theme_color, voiceAssistant.audioTrack, voiceAssistant.state]);

  const questionDescriptionContent = useMemo(() => {
    const disconnectedContent = (
      <div className="flex flex-col items-center justify-center gap-2 text-gray-700 text-center w-full h-full">
        Connect to see the question description.
      </div>
    );

    // Show question description or instructions
    return (
      <div className="flex flex-col p-4 gap-2 overflow-y-auto w-full h-full">
        {roomState === ConnectionState.Disconnected ? 
          disconnectedContent : 
          (questionDescription ? 
            <div className="prose prose-sm max-w-none h-full overflow-y-auto">
              {questionDescription.split('\n').map((line, i) => (
                <p key={i} className="text-gray-300 mb-4">{line}</p>
              ))}
            </div> : 
            <div className="flex items-center justify-center text-gray-700 h-full">
              Waiting for question...
            </div>
          )
        }
      </div>
    );
  }, [roomState, questionDescription]);

  const settingsTileContent = useMemo(() => {
    return (
      <div className="flex flex-col gap-4 h-full w-full items-start overflow-y-auto">
        <ConfigurationPanelItem title="Voice Assistant">
          {agentAudioVisualizer}
        </ConfigurationPanelItem>

        <div className="flex justify-center w-full">
          <InterviewTimer className="text-lg font-semibold" />
        </div>

        <ConfigurationPanelItem title="Status">
          <div className="flex flex-col gap-2">
            <NameValueRow
              name="Room connected"
              value={
                roomState === ConnectionState.Connecting ? (
                  <LoadingSVG diameter={16} strokeWidth={2} />
                ) : (
                  roomState.toUpperCase()
                )
              }
              valueColor={
                roomState === ConnectionState.Connected
                  ? `${config.settings.theme_color}-500`
                  : "gray-500"
              }
            />
            <NameValueRow
              name="Agent connected"
              value={
                voiceAssistant.agent ? (
                  "TRUE"
                ) : roomState === ConnectionState.Connected ? (
                  <LoadingSVG diameter={12} strokeWidth={2} />
                ) : (
                  "FALSE"
                )
              }
              valueColor={
                voiceAssistant.agent
                  ? `${config.settings.theme_color}-500`
                  : "gray-500"
              }
            />
          </div>
        </ConfigurationPanelItem>

        {localVideoTrack && (
          <ConfigurationPanelItem
            title="Camera"
            deviceSelectorKind="videoinput"
          >
            <div className="relative">
              <VideoTrack
                className="rounded-sm border border-gray-800 opacity-70 w-full"
                trackRef={localVideoTrack}
              />
            </div>
          </ConfigurationPanelItem>
        )}
        {localMicTrack && (
          <ConfigurationPanelItem
            title="Microphone"
            deviceSelectorKind="audioinput"
          >
            <AudioInputTile trackRef={localMicTrack} />
          </ConfigurationPanelItem>
        )}

        <ConfigurationPanelItem title="Settings">
          {localParticipant && (
            <div className="flex flex-col gap-2">
              <NameValueRow
                name="Room"
                value={name}
                valueColor={`${config.settings.theme_color}-500`}
              />
              <NameValueRow
                name="Participant"
                value={localParticipant.identity}
              />
            </div>
          )}
        </ConfigurationPanelItem>

        <div className="w-full">
          <ConfigurationPanelItem title="Color">
            <ColorPicker
              colors={themeColors}
              selectedColor={config.settings.theme_color}
              onSelect={(color) => {
                const userSettings = { ...config.settings };
                userSettings.theme_color = color;
                setUserSettings(userSettings);
              }}
            />
          </ConfigurationPanelItem>
        </div>
        {config.show_qr && (
          <div className="w-full">
            <ConfigurationPanelItem title="QR Code">
              <QRCodeSVG value={window.location.href} width="128" />
            </ConfigurationPanelItem>
          </div>
        )}
      </div>
    );
  }, [
    config.settings,
    config.show_qr,
    localParticipant,
    name,
    roomState,
    localVideoTrack,
    localMicTrack,
    themeColors,
    setUserSettings,
    voiceAssistant.agent,
  ]);

  let mobileTabs: PlaygroundTab[] = [];
  if (config.settings.outputs.video) {
    mobileTabs.push({
      title: "Video",
      content: (
        <PlaygroundTile
          className="w-full h-full grow"
          childrenClassName="justify-center"
        >
          {videoTileContent}
        </PlaygroundTile>
      ),
    });
  }

  if (config.settings.outputs.audio) {
    mobileTabs.push({
      title: "Audio",
      content: (
        <PlaygroundTile
          className="w-full h-full grow"
          childrenClassName="justify-center"
        >
          {agentAudioVisualizer}
        </PlaygroundTile>
      ),
    });
  }

  if (config.settings.chat) {
    mobileTabs.push({
      title: "Chat",
      content: chatTileContent,
    });
  }

  mobileTabs.push({
    title: "Settings",
    content: (
      <PlaygroundTile
        padding={false}
        backgroundColor="gray-950"
        className="h-full w-full basis-1/4 items-start overflow-y-auto flex"
        childrenClassName="h-full grow items-start"
      >
        {settingsTileContent}
      </PlaygroundTile>
    ),
  });

  // Update the code editor onChange handler
  const handleCodeChange = useCallback(
    (newCode: string) => {
      setUserCode(newCode);

      if (roomState === ConnectionState.Connected && localParticipant) {
        const payload = {
          type: "code_update",
          code: newCode,
          timestamp: Date.now(),
        };

        localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(payload)),
          { topic: "code" }
        );
      }
    },
    [localParticipant, roomState]
  );

  // Handle resize mouse events
  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizingRef.current = true;
    startYRef.current = e.clientY;
    startHeightRef.current = descriptionHeight;
    
    console.log("Resize started", { 
      startY: startYRef.current, 
      startHeight: startHeightRef.current 
    });
    
    // Add event listeners for mouse move and up
    document.addEventListener('mousemove', handleResizeMouseMove);
    document.addEventListener('mouseup', handleResizeMouseUp);
  }, [descriptionHeight]);

  const handleResizeMouseMove = useCallback((e: MouseEvent) => {
    if (!resizingRef.current) return;
    
    const diff = e.clientY - startYRef.current;
    const newHeight = Math.max(100, Math.min(500, startHeightRef.current + diff));
    console.log("Resizing", { 
      currentY: e.clientY, 
      diff, 
      newHeight 
    });
    setDescriptionHeight(newHeight);
  }, []);

  const handleResizeMouseUp = useCallback(() => {
    resizingRef.current = false;
    console.log("Resize ended");
    document.removeEventListener('mousemove', handleResizeMouseMove);
    document.removeEventListener('mouseup', handleResizeMouseUp);
  }, [handleResizeMouseMove]);

  // Clean up event listeners
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleResizeMouseMove);
      document.removeEventListener('mouseup', handleResizeMouseUp);
    };
  }, [handleResizeMouseMove, handleResizeMouseUp]);

  return (
    <>
      <PlaygroundHeader
        title={config.title}
        height={headerHeight}
        accentColor={config.settings.theme_color}
        connectionState={roomState}
        onConnectClicked={() =>
          onConnect(roomState === ConnectionState.Disconnected)
        }
      />
      <div className="flex gap-4 py-4 grow w-full h-[calc(100vh-56px)] min-h-0 overflow-hidden">
        <div className="flex flex-col basis-1/2 gap-4 h-full min-h-0 overflow-hidden">
          <PlaygroundTile
            title="Problem"
            className="w-full h-full min-h-0 overflow-hidden"
          >
            <CodeEditor
              value={userCode}
              onChange={handleCodeChange}
              language="python"
              theme="vs-dark"
              placeholder="Write your solution here..."
            />
          </PlaygroundTile>
        </div>

        <div className="flex flex-col basis-[30%] gap-0 h-full min-h-0 overflow-hidden">
          <PlaygroundTile
            title="Question Description"
            className="w-full overflow-hidden"
            style={{ height: `${descriptionHeight}px` }}
            childrenClassName="justify-start"
          >
            {questionDescriptionContent}
          </PlaygroundTile>
          
          {/* Resize handle - made more visible for debugging */}
          <div 
            className="w-full h-6 hover:bg-gray-600 cursor-ns-resize flex items-center justify-center relative z-10"
            onMouseDown={handleResizeMouseDown}
            onClick={() => console.log("Resize handle clicked")}
          >
            <div className="w-16 h-2 bg-gray-500 rounded-full"></div>
          </div>

          {config.settings.chat && (
            <PlaygroundTile
              title="Interview Chat"
              className="w-full flex-1 min-h-0 overflow-hidden"
              childrenClassName="h-full flex flex-col gap-2"
            >
              {chatTileContent}
            </PlaygroundTile>
          )}
        </div>

        <PlaygroundTile
          padding={false}
          backgroundColor="gray-950"
          className="basis-1/5 h-full min-h-0 overflow-hidden"
          childrenClassName="h-full grow items-start overflow-y-auto"
        >
          {settingsTileContent}
        </PlaygroundTile>
      </div>
    </>
  );
}
