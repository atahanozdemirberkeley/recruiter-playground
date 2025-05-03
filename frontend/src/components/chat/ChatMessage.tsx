type ChatMessageProps = {
  message: string;
  accentColor: string;
  name: string;
  isSelf: boolean;
  hideName?: boolean;
};

export const ChatMessage = ({
  name,
  message,
  accentColor,
  isSelf,
  hideName,
}: ChatMessageProps) => {
  // Function to handle different color formats
  const getColorStyle = () => {
    // If accentColor starts with '#', use it directly
    if (accentColor.startsWith('#')) {
      return { color: accentColor };
    }
    
    // For named colors like 'cyan', use Tailwind classes instead of inline styles
    return {};
  };

  return (
    <div className={`flex flex-col ${hideName ? "mt-1" : "mt-4"} items-start w-full`}>
      {!hideName && (
        <div className="flex items-center mb-1">
          <div
            className={`font-medium text-xs ${
              isSelf ? "text-gray-400" : !accentColor.startsWith('#') ? `text-${accentColor}-500` : ""
            }`}
            style={!isSelf && accentColor.startsWith('#') ? {color: accentColor} : {}}
          >
            {name}
          </div>
        </div>
      )}
      <div
        className={`px-3 py-2 rounded-md w-full text-sm whitespace-pre-line border-b border-gray-700/30 ${
          !isSelf && !accentColor.startsWith('#') ? `text-${accentColor}-500` : (isSelf ? "text-white" : "")
        }`}
        style={!isSelf && accentColor.startsWith('#') ? {color: accentColor} : {}}
      >
        {message}
      </div>
    </div>
  );
};
