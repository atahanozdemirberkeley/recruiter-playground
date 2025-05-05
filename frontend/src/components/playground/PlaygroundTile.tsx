import { ReactNode, useState } from "react";
import { useLocalParticipant, useConnectionState } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { useConfig } from "src/hooks/useConfig";

const titleHeight = 40; // Increased height for better visual

export interface PlaygroundTileProps {
  title?: string;
  children?: ReactNode;
  className?: string;
  childrenClassName?: string;
  padding?: boolean;
  backgroundColor?: string;
  actions?: ReactNode;
  style?: React.CSSProperties;
}

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
  style,
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
      className={`flex flex-col glass-panel perspective-tilt ${className} rounded-3xl overflow-hidden backdrop-blur-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] bg-recurit-blue/30 border border-recurit-blue/20 text-gray-300 transition-all duration-300 perspective-hover`}
      style={{...style, transformStyle: 'preserve-3d'}}
    >
      {title && (
        <div
          className={`flex items-center justify-between border-b border-gray-800/40 backdrop-blur-sm ${
            title === "Problem"
              ? "bg-recurit-dark/70 px-5 py-4" // Problem header has special styling
              : "px-4 py-3"
          }`}
        >
          <h2 className={`font-medium ${title === "Problem" ? "header-gradient text-lg" : "text-white text-sm"}`}>{title}</h2>
          <div className="flex gap-4 items-center translate-z-4" style={{transform: 'translateZ(4px)'}}>
            {title === "Problem" && (
              <div className="flex">
                <button 
                  className="px-4 py-1.5 bg-recurit-dark hover:bg-recurit-blue text-gray-300 rounded-l-lg text-sm border border-transparent hover:border-recurit-blue/40 transition-all duration-300"
                  onClick={() => sendDataMessage("run_code")}
                >
                  Run
                </button>
                <button 
                  className={`px-4 py-1.5 bg-recurit-accent hover:bg-recurit-accent/80 text-white rounded-r-lg text-sm transition-all duration-300 shadow-recurit`}
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
        className={`flex flex-col h-full w-full overflow-hidden ${childrenClassName}`}
        style={{
          padding: title === "Problem" ? "0" : `${contentPadding * 4}px`,
          transformStyle: 'preserve-3d',
        }}
      >
        {/* Add decorative blurred elements */}
        <div className="decorative-blur w-24 h-24 -top-8 -right-8 bg-recurit-accent/20"></div>
        <div className="decorative-blur w-16 h-16 bottom-12 left-4 bg-recurit-purple/10"></div>
        
        {/* Main content */}
        <div className="relative z-10 h-full w-full" style={{transform: 'translateZ(4px)'}}>
          {children}
        </div>
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
      className={`flex flex-col h-full glass-panel rounded-3xl overflow-hidden text-gray-300 transition-all duration-300 perspective-hover ${className}`}
      style={{transformStyle: 'preserve-3d'}}
    >
      <div
        className="flex items-center justify-start border-b border-gray-800/40 backdrop-blur-sm bg-recurit-dark/70"
        style={{
          height: `${titleHeight}px`,
          transformStyle: 'preserve-3d',
        }}
      >
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`px-4 py-3 font-medium text-sm transition-all duration-300 border-r border-r-gray-800/30 ${
              index === activeTab
                ? `bg-recurit-blue/30 text-white shadow-[inset_0_2px_0_${config.settings.theme_color}]`
                : `bg-transparent text-gray-400 hover:text-white hover:bg-recurit-blue/20`
            }`}
            onClick={() => setActiveTab(index)}
            style={{transform: index === activeTab ? 'translateZ(8px)' : 'translateZ(0)'}}
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
          transformStyle: 'preserve-3d',
        }}
      >
        <div className="decorative-blur w-24 h-24 -top-8 -right-8 bg-recurit-accent/20"></div>
        <div className="relative z-10 h-full w-full" style={{transform: 'translateZ(4px)'}}>
          {tabs[activeTab].content}
        </div>
      </div>
    </div>
  );
};
