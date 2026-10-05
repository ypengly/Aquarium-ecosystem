import type { EventWire, Frame, StatsWire } from './protocol';

export interface Sample { x: number; y: number; h: number; t: number }

export interface Entity {
  id: number; species: string; size: number;
  prev: Sample; next: Sample;
  state: string; energy: number; hunger: number;
}

export interface FoodEntity { id: number; x: number; y: number }

export interface Pose { x: number; y: number; h: number; speed: number }

function lerpAngle(a: number, b: number, t: number): number {
  const d = ((b - a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  return a + d * t;
}

/**
 * Client-side mirror of the aquarium, built from SNAPSHOT/DELTA messages.
 * Rendering runs at 60 FPS and interpolates between the two most recent server samples,
 * drawing the world ~2 ticks in the past so there is always something to interpolate toward.
 */
export class WorldState {
  creatures = new Map<number, Entity>();
  food = new Map<number, FoodEntity>();
  tick = 0;
  stats: StatsWire | null = null;
  readonly tickMs: number;
  onEvent: (e: EventWire) => void = () => {};

  constructor(tickRate: number) {
    this.tickMs = 1000 / tickRate;
  }

  get renderDelayMs(): number {
    return this.tickMs * 2;
  }

  apply(f: Frame, now: number): void {
    if (f.type === 'SNAPSHOT') {
      this.creatures.clear();
      this.food.clear();
    }
    for (const c of f.add ?? []) {
      const s: Sample = { x: c.x, y: c.y, h: c.h, t: now };
      this.creatures.set(c.i, {
        id: c.i, species: c.sp ?? '', size: c.z ?? 14, prev: s, next: s, state: c.s, energy: c.e, hunger: c.hu,
      });
    }
    for (const c of f.upd ?? []) {
      const e = this.creatures.get(c.i);
      if (!e) continue;
      // a creature that was quiet for a while must not "slide" from its old position
      e.prev = now - e.next.t > this.tickMs * 1.5
        ? { x: e.next.x, y: e.next.y, h: e.next.h, t: now - this.tickMs }
        : e.next;
      e.next = { x: c.x, y: c.y, h: c.h, t: now };
      e.state = c.s;
      e.energy = c.e;
      e.hunger = c.hu;
    }
    for (const id of f.rem ?? []) this.creatures.delete(id);
    for (const fd of [...(f.fadd ?? []), ...(f.fupd ?? [])]) this.food.set(fd.i, { id: fd.i, x: fd.x, y: fd.y });
    for (const id of f.frem ?? []) this.food.delete(id);
    this.tick = f.tick;
    if (f.stats) this.stats = f.stats;
    for (const ev of f.events ?? []) this.onEvent(ev);
  }

  pose(e: Entity, renderTime: number): Pose {
    const { prev, next } = e;
    const span = next.t - prev.t;
    const a = span <= 0 ? 1 : Math.min(1, Math.max(0, (renderTime - prev.t) / span));
    const x = prev.x + (next.x - prev.x) * a;
    const y = prev.y + (next.y - prev.y) * a;
    const speed = span > 0 ? (Math.hypot(next.x - prev.x, next.y - prev.y) / span) * 1000 : 0;
    return { x, y, h: lerpAngle(prev.h, next.h, a), speed };
  }
}
