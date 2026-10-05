import Phaser from 'phaser';
import { Connection } from './networking/Connection';
import { WorldState } from './networking/WorldState';
import { Hud } from './ui/Hud';
import { AquariumScene, type App } from './scenes/AquariumScene';
import type { Welcome } from './networking/protocol';

const aquarium = new URLSearchParams(location.search).get('aquarium') ?? 'default';
const conn = new Connection(Connection.urlFor(aquarium));
const hud = new Hud(document.getElementById('hud') as HTMLElement);
let app: App | null = null;

function startGame(w: Welcome, a: App): void {
  const game = new Phaser.Game({
    type: Phaser.WEBGL,
    parent: 'game',
    width: w.world.width,
    height: w.world.height,
    backgroundColor: '#021419',
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    render: { antialias: true },
  });
  game.scene.add('aquarium', AquariumScene, true, a);
}

conn.set({
  status: (s) => hud.setStatus(s),
  welcome: (w) => {
    if (app) {            // reconnect: the SNAPSHOT that follows resets the mirrored state
      app.welcome = w;
      return;
    }
    const state = new WorldState(w.world.tickRate);
    state.onEvent = (e) => { if (e.kind !== 'spawn') hud.pushEvent(e.text); };
    app = { conn, state, hud, welcome: w, inspection: null, selected: null };
    hud.setSpecies(w.world.species);
    hud.onAdd = (species) => conn.send({
      type: 'ADD_CREATURE', species,
      x: 80 + Math.random() * (w.world.width - 160), y: w.world.height * (0.2 + Math.random() * 0.4),
    });
    startGame(w, app);
  },
  frame: (f) => app?.state.apply(f, performance.now()),
  inspection: (m) => {
    if (app && m.id === app.selected) {
      app.inspection = m;
      hud.showInspection(m);
    }
  },
  error: (m) => hud.pushEvent(`Server: ${m.message}`),
});
conn.connect();
