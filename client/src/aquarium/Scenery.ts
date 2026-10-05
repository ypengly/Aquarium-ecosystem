import Phaser from 'phaser';
import type { WorldDesc } from '../networking/protocol';

/** Purely visual: nothing here feeds back into the simulation. */
export function buildScenery(scene: Phaser.Scene, w: WorldDesc): void {
  const W = w.width, H = w.height;

  // water column
  const water = scene.add.graphics().setDepth(0);
  water.fillGradientStyle(0x0d4553, 0x0d4553, 0x021419, 0x021419, 1);
  water.fillRect(0, 0, W, H);

  // light shafts from above
  for (let i = 0; i < 7; i++) {
    const shaft = scene.add.image(120 + i * (W / 7), -40, 'shaft')
      .setOrigin(0.5, 0).setDepth(1).setAlpha(0.07 + (i % 3) * 0.02).setAngle(-9 + (i % 2) * 3)
      .setScale(0.8 + (i % 3) * 0.5, 1.1).setBlendMode(Phaser.BlendModes.ADD);
    scene.tweens.add({
      targets: shaft, x: shaft.x + 40 + i * 6, alpha: shaft.alpha * 0.4, duration: 7000 + i * 900,
      yoyo: true, repeat: -1, ease: 'Sine.easeInOut',
    });
  }

  // sand floor
  const sand = scene.add.graphics().setDepth(3);
  sand.fillStyle(0x8a7551, 1).beginPath().moveTo(0, H);
  for (let x = 0; x <= W; x += 40) sand.lineTo(x, w.floorY + 6 + Math.sin(x * 0.012) * 9 + Math.sin(x * 0.04) * 3);
  sand.lineTo(W, H).closePath().fillPath();
  sand.fillStyle(0x5e4f35, 0.55).fillRect(0, H - 34, W, 34);

  // rocks (solid in the simulation)
  for (const r of w.rocks) {
    const g = scene.add.graphics().setDepth(5);
    g.fillStyle(0x2c3a42, 1).fillEllipse(r.x, r.y + r.r * 0.12, r.r * 2.1, r.r * 1.75);
    g.fillStyle(0x4a5b65, 1).fillEllipse(r.x - r.r * 0.12, r.y - r.r * 0.1, r.r * 1.7, r.r * 1.4);
    g.fillStyle(0x6a7d88, 0.7).fillEllipse(r.x - r.r * 0.3, r.y - r.r * 0.4, r.r * 0.8, r.r * 0.45);
  }

  // plant clumps (hiding places in the simulation)
  const greens = [0x2f8f62, 0x3fae6f, 0x256f50, 0x5bbf7a];
  for (const s of w.shelters) {
    const baseY = Math.min(w.floorY + 4, s.y + s.r * 0.75);
    for (let i = 0; i < 10; i++) {
      const front = i % 5 === 0;
      const b = scene.add.image(s.x + (i - 4.5) * (s.r / 6), baseY, 'blade')
        .setOrigin(0.5, 1).setDepth(front ? 14 : 4)
        .setTint(greens[i % greens.length]).setAlpha(front ? 0.9 : 0.85)
        .setScale(0.7 + (i % 3) * 0.25, (s.r * (1.2 + (i % 4) * 0.2)) / 200);
      b.setAngle(-6 + (i % 5) * 3);
      scene.tweens.add({
        targets: b, angle: b.angle + 7 + (i % 3) * 2, duration: 2400 + i * 260,
        yoyo: true, repeat: -1, ease: 'Sine.easeInOut', delay: i * 120,
      });
    }
  }

  // drifting particles + a bubbler
  scene.add.particles(0, 0, 'mote', {
    x: { min: 0, max: W }, y: { min: 0, max: w.floorY }, lifespan: 12000, speedY: { min: -6, max: 2 },
    speedX: { min: -5, max: 5 }, scale: { start: 0.5, end: 0.2 }, alpha: { start: 0, end: 0.35 },
    frequency: 180, quantity: 1,
  }).setDepth(2);
  scene.add.particles(0, 0, 'bubble', {
    x: { min: 118, max: 126 }, y: w.floorY - 6, lifespan: 5500, speedY: { min: -90, max: -60 },
    speedX: { min: -10, max: 10 }, scale: { start: 0.4, end: 1.0 }, alpha: { start: 0.9, end: 0 },
    frequency: 140, quantity: 1,
  }).setDepth(13);
}
