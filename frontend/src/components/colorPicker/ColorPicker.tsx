import { useState } from "react";

type ColorPickerProps = {
  colors: string[];
  selectedColor: string;
  onSelect: (color: string) => void;
};

export const ColorPicker = ({
  colors,
  selectedColor,
  onSelect,
}: ColorPickerProps) => {
  return (
    <div className="flex flex-row gap-1 py-2 flex-wrap">
      {colors.map((color) => {
        const isSelected = color === selectedColor;
        const borderColor = isSelected
          ? `border border-${color}-800`
          : "border-transparent";
        return (
          <div
            key={color}
            className={`rounded-md p-1 border-2 ${borderColor} cursor-pointer opacity-100 ${isSelected ? "opacity-100" : ""}`}
            onClick={() => {
              onSelect(color);
            }}
          >
            <div className={`w-5 h-5 bg-${color}-500 rounded-sm`}></div>
          </div>
        );
      })}
    </div>
  );
};
