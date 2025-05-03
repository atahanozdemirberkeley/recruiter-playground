import React, { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = {
  accentColor: string;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export const Button: React.FC<ButtonProps> = ({
  accentColor,
  children,
  className,
  disabled,
  ...allProps
}) => {
  return (
    <button
      className={`flex items-center justify-center ${
        disabled ? "opacity-60 pointer-events-none" : ""
      } text-sm px-4 py-2 rounded-lg backdrop-blur-sm 
      ${accentColor === 'recurit' || accentColor === 'recurit-accent' 
        ? 'bg-recurit-accent hover:bg-recurit-accent/80 text-white' 
        : `bg-${accentColor}-500/80 text-white hover:bg-${accentColor}-600/90`}
      transition-all duration-300 hover:shadow-${accentColor} hover:-translate-y-0.5 
      border border-${accentColor === 'recurit' || accentColor === 'recurit-accent' 
        ? 'recurit-purple/30' 
        : `${accentColor}-400/30`} 
      active:translate-y-0 active:shadow-none ${className}`}
      style={{transform: 'translateZ(4px)'}}
      {...allProps}
    >
      {children}
    </button>
  );
};
