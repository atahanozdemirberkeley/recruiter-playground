import Editor, { Monaco } from "@monaco-editor/react";
import { useEffect, useRef, useCallback } from "react";
import { ConnectionState } from "../../types/ConnectionState";

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language: string;
  theme: string;
  placeholder?: string;
}

export const CodeEditor = ({
  value,
  onChange,
  language,
  theme,
  placeholder,
}: CodeEditorProps) => {
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor: any, monaco: Monaco) => {
    editorRef.current = editor;

    // Configure editor with LeetCode-like theme
    monaco.editor.defineTheme("leetcode-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#1a1a1a",
        "editor.foreground": "#eff1f6",
        "editor.lineHighlightBackground": "#1a1a1a",
        "editorLineNumber.foreground": "#666666",
        "editor.selectionBackground": "#264f78",
        "editor.inactiveSelectionBackground": "#264f7855",
        "scrollbarSlider.background": "#79797966",
        "scrollbarSlider.hoverBackground": "#646464b3",
        "scrollbarSlider.activeBackground": "#bfbfbf66",
      },
    });

    monaco.editor.setTheme("leetcode-dark");
  };

  return (
    <Editor
      height="100%"
      defaultLanguage={language}
      defaultValue={placeholder}
      value={value}
      theme={theme}
      onChange={(value) => onChange(value || "")}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "on",
        roundedSelection: false,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        padding: { top: 16, bottom: 16 },
        folding: true,
        lineDecorationsWidth: 0,
        lineNumbersMinChars: 3,
        renderLineHighlight: "none", // Removes line highlight
        scrollbar: {
          useShadows: false,
          verticalScrollbarSize: 8,
          horizontalScrollbarSize: 8,
        },
      }}
      onMount={handleEditorDidMount}
    />
  );
};
