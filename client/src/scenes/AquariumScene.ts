import Phaser from 'phaser';
import type { Connection } from '../networking/Connection';
import type { Inspection, Welcome } from '../networking/protocol';
import type { WorldState } from '../networking/WorldState';
import type { Hud } from '../ui/Hud';
import { CreatureView } from '../creatures/CreatureView';
import { buildScenery } from '../aquarium/Scenery';
import { makeFishTexture, makeMiscTextures } from '../rendering/textures';

export interface App {
  conn: Connection;
  state: WorldState;
  hud: Hud;
  welcome: Welcome;
  inspection: Inspection | null;
  selected: number | null;
}

/** Renders the mirrored world at 60 FPS and turns clicks into server messages. It makes no simulation decisions. */
export class AquariumScene extends Phaser.Scene {
  private app!: App;
  private views = new Map<number, CreatureView>();
  private food = new Map<number, Phaser.GameObjects.Image>();
  private overlay!: Phaser.GameObjects.Graphics;
  private poll = 0;
  private lastHud = 0;

  constructor() {
    super('aquarium');
  }

  init(app: App): void {
    this.app = app;
  }

  create(): void {
    const world = this.app.welcome.world;
    for (const sp of world.species) makeFishTexture(this, sp);
    makeMiscTextures(this);
    buildScenery(this, world);
    this.overlay = this.add.graphics().setDepth(30);

    this.input.on('pointerdown', this.onPointer, this);
    this.app.hud.onDeselect = () => this.select(null);
    this.poll = window.setInterval(() => {
      if (this.app.selected !== null) this.app.conn.send({ type: 'INSPECT', id: this.app.selected });
    }, 250);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => window.clearInterval(this.poll));
  }

  private select(id: number | null): void {
    this.app.selected = id;
    this.app.inspection = null;
    if (id === null) this.app.hud.clearInspection();
    else this.app.conn.send({ type: 'INSPECT', id });
  }

  private onPointer(p: Phaser.Input.Pointer): void {
    const rt = performance.now() - this.app.state.renderDelayMs;
    let best: number | null = null;
    let bestD = Infinity;
    for (const e of this.app.state.creatures.values()) {
      const v = this.views.get(e.id);
      if (!v) continue;
      const pose = this.app.state.pose(e, rt);
      const d = Math.hypot(pose.x - p.worldX, pose.y - p.worldY);
      if (d <= v.radius + 4 && d < bestD) { best = e.id; bestD = d; }
    }
    if (best !== null) this.select(best);
    else this.app.conn.send({ type: 'FEED', x: p.worldX });
  }

  update(time: number): void {
    const st = this.app.state;
    const rt = performance.now() - st.renderDelayMs;
    const tsec = time / 1000;
    const showState = this.app.hud.toggles.state;

    for (const e of st.creatures.values()) {
      let v = this.views.get(e.id);
      if (!v) {
        v = new CreatureView(this, e.species, e.size);
        this.views.set(e.id, v);
      }
      const p = st.pose(e, rt);
      v.setPose(p.x, p.y, p.h, p.speed, tsec);
      if (showState) v.setLabel(this, e.state.toLowerCase().replace(/_/g, ' '));
      else if (v.label) v.setLabel(this, null);
    }
    for (const [id, v] of this.views) {
      if (!st.creatures.has(id)) {
        v.destroy();
        this.views.delete(id);
        if (this.app.selected === id) this.select(null);
      }
    }

    for (const f of st.food.values()) {
      let s = this.food.get(f.id);
      if (!s) {
        s = this.add.image(f.x, f.y, 'flake').setDepth(9).setScale(0.7);
        this.food.set(f.id, s);
      }
      s.setPosition(f.x, f.y).setRotation(f.id + tsec * 0.6);
    }
    for (const [id, s] of this.food) {
      if (!st.food.has(id)) { s.destroy(); this.food.delete(id); }
    }

    this.drawOverlay(rt);
    if (time - this.lastHud > 250) {
      this.lastHud = time;
      this.app.hud.setStats(st.tick, st.stats, this.game.loop.actualFps);
    }
  }

  private drawOverlay(rt: number): void {
    const g = this.overlay;
    const st = this.app.state;
    const tg = this.app.hud.toggles;
    const species = new Map(this.app.welcome.world.species.map((s) => [s.key, s]));
    g.clear();

    if (tg.vision) {
      const ids = this.app.selected !== null ? [this.app.selected] : [...st.creatures.keys()];
      for (const id of ids) {
        const e = st.creatures.get(id);
        if (!e) continue;
        const p = st.pose(e, rt);
        const r = id === this.app.selected && this.app.inspection ? this.app.inspection.vision : species.get(e.species)?.vision ?? 150;
        g.fillStyle(0x7fe3ff, 0.04).fillCircle(p.x, p.y, r);
        g.lineStyle(1, 0x7fe3ff, 0.35).strokeCircle(p.x, p.y, r);
      }
    }

    if (this.app.selected === null) return;
    const e = st.creatures.get(this.app.selected);
    const v = this.views.get(this.app.selected);
    if (!e || !v) return;
    const p = st.pose(e, rt);
    g.lineStyle(2, 0xffcf7a, 0.95).strokeCircle(p.x, p.y, v.radius + 6);

    const ins = this.app.inspection;
    if (tg.target && ins && ins.id === e.id && ins.target) {
      g.lineStyle(1.5, 0xffcf7a, 0.55).lineBetween(p.x, p.y, ins.target.x, ins.target.y);
      g.strokeCircle(ins.target.x, ins.target.y, 7);
    }
  }
}
