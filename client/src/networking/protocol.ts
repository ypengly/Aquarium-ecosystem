// Wire types shared with the Go world server (see server/internal/delta and server/internal/world).

export interface CircleDesc { x: number; y: number; r: number }

export interface SpeciesDesc {
  key: string; name: string; size: number; vision: number; color: number; stripe: number; trophic: string;
}

export interface WorldDesc {
  width: number; height: number; floorY: number; tickRate: number;
  rocks: CircleDesc[]; shelters: CircleDesc[]; species: SpeciesDesc[];
}

export interface CreatureWire {
  i: number; sp?: string; x: number; y: number; h: number; s: string; e: number; hu: number; z?: number;
}
export interface FoodWire { i: number; k?: string; x: number; y: number }
export interface EventWire { tick: number; kind: string; text: string; creatureId: number }
export interface StatsWire { stepMs: number; decisions: number; creatures: number; food: number }

export interface Welcome { type: 'WELCOME'; aquariumId: string; world: WorldDesc; serverTime: number }

export interface Frame {
  type: 'SNAPSHOT' | 'DELTA';
  tick: number; time: number;
  add?: CreatureWire[]; upd?: CreatureWire[]; rem?: number[];
  fadd?: FoodWire[]; fupd?: FoodWire[]; frem?: number[];
  events?: EventWire[]; stats?: StatsWire;
}

export interface Inspection {
  type: 'INSPECTION';
  id: number; name: string; species: string; age: number;
  health: number; energy: number; hunger: number; safety: number; social: number;
  personality: string; mood: string; state: string; goal: string;
  genes: Record<string, number>; traits: Record<string, number>;
  scores: { action: string; score: number }[];
  memories: { kind: string; x: number; y: number; strength: number }[];
  recent: string[];
  target?: { x: number; y: number };
  vision: number;
}

export interface ErrorMsg { type: 'ERROR'; code: string; message: string }

export type ServerMessage = Welcome | Frame | Inspection | ErrorMsg;
