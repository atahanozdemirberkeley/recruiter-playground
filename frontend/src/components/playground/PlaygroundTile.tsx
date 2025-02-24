import { ReactNode, useState } from "react";
import { useLocalParticipant, useConnectionState } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { useConfig } from "src/hooks/useConfig";

const titleHeight = 32;

type PlaygroundTileProps = {
  title?: string;
  children?: ReactNode;
  className?: string;
  childrenClassName?: string;
  padding?: boolean;
  backgroundColor?: string;
  actions?: ReactNode;
};

export type PlaygroundTab = {
  title: string;
  content: ReactNode;
};

export type PlaygroundTabbedTileProps = {
  tabs: PlaygroundTab[];
  initialTab?: number;
} & PlaygroundTileProps;

export const PlaygroundTile: React.FC<PlaygroundTileProps> = ({
  children,
  title,
  className,
  childrenClassName,
  padding = true,
  backgroundColor = "transparent",
  actions,
}) => {
  const contentPadding = padding ? 4 : 0;
  const { localParticipant } = useLocalParticipant();
  const connectionState = useConnectionState();
  const { config } = useConfig();

  const sendDataMessage = (type: string) => {
    if (connectionState === ConnectionState.Connected && localParticipant) {
      console.log("Sending data message:", type);
      const payload = {
        type,
        timestamp: Date.now(),
      };

      localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(payload)),
        { topic: "code" }
      );
    }
  };

  return (
    <div
      className={`flex flex-col ${className} ${
        title === "Problem"
          ? "bg-[#1a1a1a] rounded-lg overflow-hidden shadow-lg" // LeetCode-style container
          : `border rounded-sm border-gray-800 text-gray-500 bg-${backgroundColor}`
      }`}
    >
      {title && (
        <div
          className={`flex items-center justify-between ${
            title === "Problem"
              ? "bg-[#282828] px-5 py-4 text-[#eff1f6] text-base border-b border-[#3c3c3c]" // LeetCode-style header
              : "justify-center text-xs uppercase py-2 px-4 border-b border-gray-800 tracking-wider"
          }`}
        >
          <h2 className={title === "Problem" ? "font-medium" : ""}>{title}</h2>
          <div className="flex gap-4 items-center">
            {title === "Problem" && (
              <div className="flex">
                <button className="px-4 py-1.5 bg-[#454545] hover:bg-[#565656] text-gray-300 rounded-l text-sm border border-transparent hover:border-[#6b6b6b]"
                onClick={() => sendDataMessage("run_code")}
                >
                  Run
                </button>
                <button className={`px-4 py-1.5 bg-${config.settings.theme_color}-600 hover:bg-${config.settings.theme_color}-700 text-white rounded-r text-sm border-l border-[#6b6b6b]`}
                onClick={() => sendDataMessage("submit_code")}
                >
                  Submit
                </button>
              </div>
            )}
            {actions && <div className="flex items-center ml-4">{actions}</div>}
          </div>
        </div>
      )}
      <div
        className={`flex flex-col grow w-full ${childrenClassName}`}
        style={{
          padding: title === "Problem" ? "0" : `${contentPadding * 4}px`,
        }}
      >
        {children}
      </div>
    </div>
  );
};

export const PlaygroundTabbedTile: React.FC<PlaygroundTabbedTileProps> = ({
  tabs,
  initialTab = 0,
  className,
  childrenClassName,
  backgroundColor = "transparent",
}) => {
  const contentPadding = 4;
  const [activeTab, setActiveTab] = useState(initialTab);
  if (activeTab >= tabs.length) {
    return null;
  }
  return (
    <div
      className={`flex flex-col h-full border rounded-sm border-gray-800 text-gray-500 bg-${backgroundColor} ${className}`}
    >
      <div
        className="flex items-center justify-start text-xs uppercase border-b border-b-gray-800 tracking-wider"
        style={{
          height: `${titleHeight}px`,
        }}
      >
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`px-4 py-2 rounded-sm hover:bg-gray-800 hover:text-gray-300 border-r border-r-gray-800 ${
              index === activeTab
                ? `bg-gray-900 text-gray-300`
                : `bg-transparent text-gray-500`
            }`}
            onClick={() => setActiveTab(index)}
          >
            {tab.title}
          </button>
        ))}
      </div>
      <div
        className={`w-full ${childrenClassName}`}
        style={{
          height: `calc(100% - ${titleHeight}px)`,
          padding: `${contentPadding * 4}px`,
        }}
      >
        {tabs[activeTab].content}
      </div>
    </div>
  );
};
