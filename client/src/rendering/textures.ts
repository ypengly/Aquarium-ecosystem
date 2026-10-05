import Phaser from 'phaser';
import type { SpeciesDesc } from '../networking/protocol';

/** Fish bodies face +x and are drawn procedurally (no art assets needed). Canvas 64x36, body length ~56px. */
export const FISH_LENGTH = 56;

function hex(n: number): number {
  return n & 0xffffff;
}

function shade(color: number, f: number): number {
  const r = Math.min(255, Math.round(((color >> 16) & 255) * f));
  const g = Math.min(255, Math.round(((color >> 8) & 255) * f));
  const b = Math.min(255, Math.round((color & 255) * f));
  return (r << 16) | (g << 8) | b;
}

export function fishKey(species: string): string {
  return `fish_${species}`;
}

export function makeFishTexture(scene: Phaser.Scene, sp: SpeciesDesc): void {
  const g = scene.add.graphics();
  const body = hex(sp.color);
  const accent = hex(sp.stripe);
  const cy = 18;

  // tail + fins first so the body overlaps their roots
  const tail = sp.key === 'blue_tang' ? accent : shade(body, 0.8);
  g.fillStyle(tail, 1).fillTriangle(44, cy, 64, cy - 15, 64, cy + 15);
  g.fillStyle(shade(body, 0.7), 1).fillTriangle(20, cy - 7, 36, cy - 7, sp.key === 'reef_shark' ? 28 : 26, cy - 17);
  g.fillStyle(shade(body, 0.75), 1).fillTriangle(24, cy + 7, 36, cy + 7, 30, cy + 14);

  // body
  g.fillStyle(body, 1).fillEllipse(28, cy, 52, 22);
  g.fillStyle(shade(body, 1.35), 1).fillEllipse(28, cy + 4, 44, 10);          // paler belly

  switch (sp.key) {
    case 'neon_tetra':
      g.fillStyle(0x7ff2ff, 1).fillRect(8, cy - 3, 38, 3);                      // electric stripe
      g.fillStyle(accent, 1).fillEllipse(36, cy + 6, 26, 7);                    // red flank
      break;
    case 'blue_tang':
      g.fillStyle(0x0b1b52, 1).fillEllipse(30, cy - 1, 30, 8);                  // dark palette marking
      break;
    case 'oscar':
      g.fillStyle(accent, 0.9).fillEllipse(22, cy - 3, 9, 7).fillEllipse(34, cy + 3, 10, 7);
      break;
    case 'reef_shark':
      g.fillStyle(accent, 1).fillEllipse(26, cy + 5, 40, 8);                    // white underside
      break;
    default:
      g.fillStyle(accent, 0.8).fillRect(18, cy - 2, 20, 3);
  }

  // eye
  g.fillStyle(0xffffff, 1).fillCircle(11, cy - 3, 3.2);
  g.fillStyle(0x0a0a0a, 1).fillCircle(11.8, cy - 3, 1.7);

  g.generateTexture(fishKey(sp.key), 64, 36);
  g.destroy();
}

export function makeMiscTextures(scene: Phaser.Scene): void {
  let g = scene.add.graphics();
  g.fillStyle(0xe8c37a, 1).fillCircle(5, 5, 4);
  g.fillStyle(0xfff0c8, 0.9).fillCircle(4, 4, 1.8);
  g.generateTexture('flake', 10, 10);
  g.destroy();

  g = scene.add.graphics();                                                   // bubble: ring + glint
  g.lineStyle(1.5, 0xcff6ff, 0.9).strokeCircle(8, 8, 6.5);
  g.fillStyle(0xffffff, 0.8).fillCircle(5.5, 5.5, 1.5);
  g.generateTexture('bubble', 16, 16);
  g.destroy();

  g = scene.add.graphics();
  g.fillStyle(0xffffff, 0.9).fillCircle(3, 3, 2);
  g.generateTexture('mote', 6, 6);
  g.destroy();

  // light shaft: vertical fade x soft horizontal edges. Built on a 2D canvas because Graphics gradients are WebGL-only
  // and generateTexture() renders through the canvas pipeline.
  const shaft = scene.textures.createCanvas('shaft', 120, 900);
  if (shaft) {
    const ctx = shaft.getContext();
    const v = ctx.createLinearGradient(0, 0, 0, 900);
    v.addColorStop(0, 'rgba(255,241,201,0.55)');
    v.addColorStop(1, 'rgba(255,241,201,0)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, 120, 900);
    const hz = ctx.createLinearGradient(0, 0, 120, 0);
    hz.addColorStop(0, 'rgba(0,0,0,0)');
    hz.addColorStop(0.5, 'rgba(0,0,0,1)');
    hz.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.globalCompositeOperation = 'destination-in';
    ctx.fillStyle = hz;
    ctx.fillRect(0, 0, 120, 900);
    shaft.refresh();
  }

  g = scene.add.graphics();                                                   // tapered plant blade, origin bottom
  g.fillStyle(0xffffff, 1);
  g.fillTriangle(0, 200, 18, 200, 9, 0);
  g.fillStyle(0xffffff, 1).fillEllipse(9, 150, 18, 120);
  g.generateTexture('blade', 18, 200);
  g.destroy();
}
