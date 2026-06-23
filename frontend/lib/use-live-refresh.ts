"use client";

import { useEffect } from "react";

export function useLiveRefresh(refresh: () => void | Promise<void>, isConnected: boolean) {
  useEffect(() => {
    function runRefresh() {
      Promise.resolve(refresh()).catch(() => {
        console.warn("Fallback HTTP refresh failed. Will retry when the page regains focus or after 60 seconds.");
      });
    }

    function handleFocus() {
      runRefresh();
    }

    window.addEventListener("focus", handleFocus);
    const interval = isConnected ? null : window.setInterval(runRefresh, 60_000);
    return () => {
      window.removeEventListener("focus", handleFocus);
      if (interval !== null) window.clearInterval(interval);
    };
  }, [isConnected, refresh]);
}
