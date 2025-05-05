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
        ? 'bg-recurit-accent/80 text-white' 
        : `bg-${accentColor}-600/90 text-white`}
      transition-all duration-300
      ${className}`}
      {...allProps}
    >
      {children}
    </button>
  );
};
