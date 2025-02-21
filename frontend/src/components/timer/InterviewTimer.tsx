import { useEffect, useState } from 'react';
import { useDataChannel } from '@livekit/components-react';

interface InterviewTimerProps {
  className?: string;
}

export const InterviewTimer = ({ className }: InterviewTimerProps) => {
  const [timeLeft, setTimeLeft] = useState<string>("00:00:00");

  const formatTimeDisplay = (timeString: string) => {
    const [hours, minutes, seconds] = timeString.split(':');
    if (hours === '00') {
      return `${minutes}:${seconds}`;
    }
    return timeString;
  };

  const handleTimeUpdate = (msg: any) => {
    if (msg.topic === 'interview-time') {
      try {
        const decodedPayload = new TextDecoder('utf-8').decode(msg.payload);
        const data = JSON.parse(decodedPayload);
        setTimeLeft(data.timeLeft);
      } catch (e) {
        console.error('Failed to parse time update:', e);
        console.error('Error details:', {
          message: e.message,
          payload: msg.payload,
        });
      }
    }
  };

  useDataChannel(handleTimeUpdate);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-gray-500">Time Remaning:</span>
      <span className="font-mono">{formatTimeDisplay(timeLeft)}</span>
    </div>
  );
}; 