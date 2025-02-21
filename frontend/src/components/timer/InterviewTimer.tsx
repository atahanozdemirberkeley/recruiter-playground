import { useEffect, useState } from 'react';
import { useDataChannel } from '@livekit/components-react';

interface InterviewTimerProps {
  className?: string;
}

export const InterviewTimer = ({ className }: InterviewTimerProps) => {
  const [timeLeft, setTimeLeft] = useState<number>(0);

  const handleTimeUpdate = (msg: any) => {
    if (msg.topic === 'interview-time') {
      try {
        const data = JSON.parse(new TextDecoder('utf-8').decode(msg.payload));
        setTimeLeft(data.timeLeft);
      } catch (e) {
        console.error('Failed to parse time update:', e);
      }
    }
  };

  useDataChannel(handleTimeUpdate);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-gray-500">Time Remaining:</span>
      <span className="font-mono">{formatTime(timeLeft)}</span>
    </div>
  );
}; 