import './hud.css';
import type { Inspection, SpeciesDesc, StatsWire } from '../networking/protocol';
import type { ConnStatus } from '../networking/Connection';

export interface Toggles { state: boolean; vision: boolean; target: boolean }

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string));
}
const pct = (v: number): number => Math.round(Math.max(0, Math.min(1, v)) * 100);
const nice = (s: string): string => s.toLowerCase().replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

/** DOM overlay: status bar, tools, creature inspector, AI visualizer and debug toggles. Fish are never DOM. */
export class Hud {
  readonly toggles: Toggles = { state: false, vision: false, target: true };
  onAdd: (species: string) => void = () => {};
  onDeselect: () => void = () => {};
  private el: Record<string, HTMLElement> = {};
  private feedLines: string[] = [];

  constructor(root: HTMLElement) {
    root.innerHTML = `
      <div id="bar" class="panel"><span class="title">Aquarium</span>
        <span><i id="status"></i><span id="statusText">connecting</span></span>
        <span id="stats"></span></div>
      <div id="tools" class="panel">
        <select id="species" aria-label="Species to add"></select>
        <button id="add" type="button">Add to tank</button>
        <span class="hint">Click open water to drop food. Click a fish to inspect it.</span>
      </div>
      <div id="debug" class="panel">
        <label><input type="checkbox" data-k="state"> AI state labels</label>
        <label><input type="checkbox" data-k="vision"> Vision radius</label>
        <label><input type="checkbox" data-k="target" checked> Selected target</label>
      </div>
      <div id="feed" class="panel"></div>
      <aside id="inspector" class="panel" hidden></aside>`;
    for (const id of ['status', 'statusText', 'stats', 'species', 'add', 'feed', 'inspector']) {
      this.el[id] = root.querySelector('#' + id) as HTMLElement;
    }
    this.el.add.addEventListener('click', () => this.onAdd((this.el.species as HTMLSelectElement).value));
    root.querySelectorAll<HTMLInputElement>('#debug input').forEach((i) =>
      i.addEventListener('change', () => { this.toggles[i.dataset.k as keyof Toggles] = i.checked; }));
    this.el.inspector.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).classList.contains('close')) this.onDeselect();
    });
  }

  setSpecies(list: SpeciesDesc[]): void {
    (this.el.species as HTMLSelectElement).innerHTML =
      list.map((s) => `<option value="${esc(s.key)}">${esc(s.name)}</option>`).join('');
  }

  setStatus(s: ConnStatus): void {
    this.el.status.className = s === 'open' ? 'open' : '';
    this.el.statusText.textContent = s === 'open' ? 'live' : s;
  }

  setStats(tick: number, st: StatsWire | null, fps: number): void {
    this.el.stats.innerHTML = [
      `Tick ${tick}`, st ? `Creatures ${st.creatures}` : '', st ? `Food ${st.food}` : '',
      st ? `Sim ${st.stepMs.toFixed(1)} ms` : '', st ? `AI ${st.decisions}/s` : '', `${Math.round(fps)} fps`,
    ].filter(Boolean).map((t) => `<span>${esc(t)}</span>`).join('');
  }

  pushEvent(text: string): void {
    this.feedLines.push(text);
    this.feedLines = this.feedLines.slice(-4);
    this.el.feed.innerHTML = this.feedLines.map((l) => `<div>${esc(l)}</div>`).join('');
    window.setTimeout(() => {
      this.feedLines.shift();
      this.el.feed.innerHTML = this.feedLines.map((l) => `<div>${esc(l)}</div>`).join('');
    }, 6000);
  }

  clearInspection(): void {
    this.el.inspector.hidden = true;
    this.el.inspector.innerHTML = '';
  }

  showInspection(m: Inspection): void {
    const bar = (label: string, v: number, cls = ''): string =>
      `<div class="row"><span>${label}</span><div class="bar ${cls}"><i style="width:${pct(v)}%"></i></div><span>${pct(v)}%</span></div>`;
    const traits = ['aggression', 'curiosity', 'fear', 'intelligence', 'sociality']
      .map((k) => bar(nice(k), m.traits[k] ?? 0)).join('');
    const scores = m.scores.map((s, i) =>
      `<div class="row ${i === 0 ? 'top' : ''}"><span>${esc(nice(s.action))}</span><div class="bar score"><i style="width:${pct(Math.min(1, s.score))}%"></i></div><span>${s.score.toFixed(2)}</span></div>`).join('');
    const recent = m.recent.length
      ? `<ul class="recent">${m.recent.map((r) => `<li>${esc(r)}</li>`).join('')}</ul>` : '<span class="muted">Nothing notable yet.</span>';
    const mem = m.memories.length
      ? m.memories.map((x) => `<div class="kv"><span class="muted">${esc(nice(x.kind))}</span><span>${pct(x.strength)}% fresh</span></div>`).join('')
      : '<span class="muted">No strong memories.</span>';
    const age = m.age < 90 ? `${Math.round(m.age)} s` : `${Math.floor(m.age / 60)} min ${Math.round(m.age % 60)} s`;
    this.el.inspector.hidden = false;
    this.el.inspector.innerHTML = `
      <button class="close" type="button" aria-label="Close">&times;</button>
      <h2>${esc(m.name)}</h2>
      <div class="muted">Age ${age}</div>
      <h3>Condition</h3>${bar('Health', m.health)}${bar('Energy', m.energy)}${bar('Hunger', m.hunger, 'hunger')}${bar('Safety', m.safety)}
      <div class="kv"><span class="muted">Personality</span><span>${esc(nice(m.personality))}</span></div>
      <div class="kv"><span class="muted">Mood</span><span>${esc(m.mood)}</span></div>
      <div class="kv"><span class="muted">State</span><span>${esc(nice(m.state))}</span></div>
      <h3>AI decision (utility scores)</h3>${scores}
      <h3>Recently</h3>${recent}
      <h3>Memory</h3>${mem}
      <h3>Temperament</h3>${traits}
      <h3>Genetics</h3>
      <div class="kv"><span class="muted">Speed</span><span>${pct((m.genes.speed ?? 1) - 0.5)}</span></div>
      <div class="kv"><span class="muted">Size</span><span>${pct((m.genes.size ?? 1) - 0.5)}</span></div>
      <div class="kv"><span class="muted">Vitality</span><span>${pct((m.genes.vitality ?? 1) - 0.5)}</span></div>`;
  }
}
