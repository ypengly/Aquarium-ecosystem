import type { ErrorMsg, Frame, Inspection, ServerMessage, Welcome } from './protocol';

export type ConnStatus = 'connecting' | 'open' | 'reconnecting';

export interface Handlers {
  status?: (s: ConnStatus) => void;
  welcome?: (m: Welcome) => void;
  frame?: (m: Frame) => void;
  inspection?: (m: Inspection) => void;
  error?: (m: ErrorMsg) => void;
}

/** WebSocket with automatic reconnect. After a reconnect the server sends WELCOME + a full SNAPSHOT again. */
export class Connection {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private url: string;
  private h: Handlers = {};

  constructor(url: string) {
    this.url = url;
  }

  static urlFor(aquarium: string): string {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}/ws?aquarium=${encodeURIComponent(aquarium)}`;
  }

  set(h: Handlers): void {
    this.h = h;
  }

  connect(): void {
    this.h.status?.(this.attempt === 0 ? 'connecting' : 'reconnecting');
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.attempt = 0;
      this.h.status?.('open');
    };
    ws.onmessage = (ev: MessageEvent) => {
      let m: ServerMessage;
      try {
        m = JSON.parse(ev.data as string) as ServerMessage;
      } catch {
        return;
      }
      switch (m.type) {
        case 'WELCOME': this.h.welcome?.(m); break;
        case 'SNAPSHOT':
        case 'DELTA': this.h.frame?.(m); break;
        case 'INSPECTION': this.h.inspection?.(m); break;
        case 'ERROR': this.h.error?.(m); break;
      }
    };
    ws.onclose = () => {
      this.h.status?.('reconnecting');
      const delay = Math.min(5000, 400 * 2 ** this.attempt++);
      window.setTimeout(() => this.connect(), delay);
    };
    ws.onerror = () => ws.close();
  }

  send(msg: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }
}
