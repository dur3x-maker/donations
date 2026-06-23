import { getStoredAccessToken } from "./api";
import type { CampaignRealtimeEvent, NotificationCreatedEvent } from "./types";

const browserApiUrl = normalizePublicApiUrl(process.env.NEXT_PUBLIC_API_URL);

function normalizePublicApiUrl(value: string | undefined) {
  if (!value) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("NEXT_PUBLIC_API_URL is required in production");
    }
    return "http://localhost:8000";
  }
  const url = new URL(value);
  if (process.env.NODE_ENV === "production" && url.protocol !== "https:" && !isLocalRuntimeHost(url.hostname)) {
    throw new Error("NEXT_PUBLIC_API_URL must use https in production");
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  return url.toString().replace(/\/$/, "");
}

function isLocalRuntimeHost(hostname: string) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "backend";
}

function getWsUrl(path: string) {
  const url = new URL(path, browserApiUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export type RealtimeStatus = "connected" | "disconnected" | "reconnecting";

function subscribe<T extends { type: string }>(
  getPath: () => string | null,
  acceptedTypes: Set<string>,
  onMessage: (event: T) => void,
  onStatus?: (status: "connected" | "disconnected" | "reconnecting") => void,
  getProtocols?: () => string[],
) {
  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let attempts = 0;
  let closed = false;

  function connect() {
    const path = getPath();
    if (!path) {
      onStatus?.("disconnected");
      return;
    }
    if (attempts > 0) {
      onStatus?.("reconnecting");
    }
    socket = new WebSocket(getWsUrl(path), getProtocols?.());

    socket.onopen = () => {
      attempts = 0;
      onStatus?.("connected");
    };

    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as T | { type: "ping" };
        if (event.type === "ping") {
          socket?.send(JSON.stringify({ type: "pong" }));
          return;
        }
        if (acceptedTypes.has(event.type)) {
          onMessage(event as T);
        }
      } catch {
        // Ignore malformed realtime payloads; the HTTP state remains the source of truth.
      }
    };

    socket.onclose = () => {
      if (closed) return;
      console.warn("Realtime connection lost. Falling back to periodic HTTP refresh.");
      onStatus?.(attempts === 0 ? "disconnected" : "reconnecting");
      const delay = Math.min(1000 * 2 ** attempts, 15000);
      attempts += 1;
      reconnectTimer = window.setTimeout(connect, delay);
    };
  }

  connect();

  return () => {
    closed = true;
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
    }
    socket?.close();
  };
}

export function subscribeCampaignUpdates(
  campaignId: string,
  onMessage: (event: CampaignRealtimeEvent) => void,
  onStatus?: (status: RealtimeStatus) => void,
) {
  return subscribe(
    () => `/ws/campaigns/${campaignId}`,
    new Set(["campaign_updated", "campaign_lifecycle_changed"]),
    onMessage,
    onStatus,
  );
}

export function subscribeCatalogUpdates(
  onMessage: (event: CampaignRealtimeEvent) => void,
  onStatus?: (status: RealtimeStatus) => void,
) {
  return subscribe(
    () => "/ws/catalog",
    new Set(["campaign_updated", "campaign_lifecycle_changed"]),
    onMessage,
    onStatus,
  );
}

export function subscribeDashboardUpdates(
  onMessage: (event: CampaignRealtimeEvent) => void,
  onStatus?: (status: RealtimeStatus) => void,
) {
  return subscribe(
    () => {
      const token = getStoredAccessToken();
      return token ? "/ws/me/dashboard" : null;
    },
    new Set(["campaign_updated", "campaign_lifecycle_changed"]),
    onMessage,
    onStatus,
    () => ["bearer", getStoredAccessToken() ?? ""],
  );
}

export function subscribeNotificationUpdates(
  onMessage: (event: NotificationCreatedEvent) => void,
  onStatus?: (status: RealtimeStatus) => void,
) {
  return subscribe(
    () => {
      const token = getStoredAccessToken();
      return token ? "/ws/me/notifications" : null;
    },
    new Set(["notification_created"]),
    onMessage,
    onStatus,
    () => ["bearer", getStoredAccessToken() ?? ""],
  );
}
