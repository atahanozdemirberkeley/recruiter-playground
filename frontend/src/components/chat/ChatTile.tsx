import { ChatMessage } from "src/components/chat/ChatMessage";
import { ChatMessageInput } from "src/components/chat/ChatMessageInput";
import { ChatMessage as ComponentsChatMessage } from "@livekit/components-react";
import { useEffect, useRef } from "react";

const inputHeight = 48;

export type ChatMessageType = {
  name: string;
  message: string;
  isSelf: boolean;
  timestamp: number;
};

type ChatTileProps = {
  messages: ChatMessageType[];
  accentColor: string;
};

export const ChatTile = ({ messages, accentColor }: ChatTileProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [containerRef, messages]);

  return (
    <div className="flex flex-col h-full">
      <div 
        ref={containerRef} 
        className="flex-1 overflow-y-auto pb-4"
      >
        <div className="flex flex-col min-h-full justify-end px-2">
          {messages.length === 0 && (
            <div className="text-center py-6 italic" style={{color: "rgb(115 115 115 / var(--tw-text-opacity, 1))"}}>
              No messages yet. The conversation will appear here.
            </div>
          )}
          {messages.map((message, index, allMsg) => {
            const hideName =
              index >= 1 && allMsg[index - 1].name === message.name;

            return (
              <ChatMessage
                key={index}
                hideName={hideName}
                name={message.name}
                message={message.message}
                isSelf={message.isSelf}
                accentColor={accentColor}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};
