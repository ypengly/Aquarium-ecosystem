import Phaser from 'phaser';
import { FISH_LENGTH, fishKey } from '../rendering/textures';

const VISUAL_SCALE = 1.9; // fish are drawn larger than their simulated body length so they read on a 1600px tank

/** Render-only wrapper. It owns a sprite and never decides anything about the creature. */
export class CreatureView {
  readonly sprite: Phaser.GameObjects.Image;
  label: Phaser.GameObjects.Text | null = null;
  private phase: number;
  readonly radius: number;

  constructor(scene: Phaser.Scene, species: string, size: number) {
    const s = (size * VISUAL_SCALE) / FISH_LENGTH;
    this.sprite = scene.add.image(0, 0, fishKey(species)).setScale(s).setDepth(10 + Math.min(3, size / 40));
    this.phase = Math.random() * Math.PI * 2;
    this.radius = size * VISUAL_SCALE * 0.55 + 6;
  }

  setPose(x: number, y: number, h: number, speed: number, timeSec: number): void {
    // tail-beat: a small rotational wiggle whose rate and size follow the swim speed
    const wiggle = Math.sin(timeSec * (4 + speed * 0.05) + this.phase) * Math.min(0.12, speed * 0.0012);
    this.sprite.setPosition(x, y).setRotation(h + wiggle).setFlipY(Math.cos(h) < 0);
    this.label?.setPosition(x, y - this.radius - 6);
  }

  setLabel(scene: Phaser.Scene, text: string | null): void {
    if (text === null) {
      this.label?.destroy();
      this.label = null;
      return;
    }
    if (!this.label) {
      this.label = scene.add.text(0, 0, text, {
        fontFamily: 'system-ui, sans-serif', fontSize: '11px', color: '#e8f6f2', stroke: '#021419', strokeThickness: 3,
      }).setOrigin(0.5, 1).setDepth(40);
    }
    this.label.setText(text);
  }

  destroy(): void {
    this.sprite.destroy();
    this.label?.destroy();
  }
}
