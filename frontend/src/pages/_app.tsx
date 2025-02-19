import { CloudProvider } from "src/cloud/useCloud";
import "@livekit/components-styles/components/participant";
import "globals.css";
import type { AppProps } from "next/app";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <CloudProvider>
      <Component {...pageProps} />
    </CloudProvider>
  );
}
