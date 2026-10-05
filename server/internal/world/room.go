// Package world owns aquarium rooms: one goroutine per room drives the Python simulation at a fixed
// tick rate and fans compact deltas out to subscribers.
package world

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"regexp"
	"sync"
	"time"

	"aquarium/server/internal/delta"
	"aquarium/server/internal/simpb"
)

// Simulator is the slice of the simulation service the world server depends on.
type Simulator interface {
	CreateWorld(ctx context.Context, id string, seed int64) (*simpb.WorldInfo, error)
	Step(ctx context.Context, id string, ticks int32) (*simpb.Snapshot, error)
	Snapshot(ctx context.Context, id string) (*simpb.Snapshot, error)
	AddFood(ctx context.Context, id string, x, y float32, count int32) (*simpb.CommandResult, error)
	AddCreature(ctx context.Context, id, species string, x, y float32) (*simpb.CommandResult, error)
	Inspect(ctx context.Context, id string, creatureID int32) (*simpb.CreatureDetail, error)
}

// Subscriber is a connected client. Send must never block; a false return means "too slow, drop me".
type Subscriber interface {
	Send(msg []byte) bool
	Close()
}

var idPattern = regexp.MustCompile(`^[a-z0-9_-]{1,32}$`)

func ValidAquariumID(id string) bool { return idPattern.MatchString(id) }

type Room struct {
	ID   string
	Desc Desc

	sim     Simulator
	mu      sync.Mutex
	subs    map[Subscriber]struct{}
	tracker *delta.Tracker
	last    delta.Frame
	welcome []byte
	cancel  context.CancelFunc
	done    chan struct{}
}

func newRoom(ctx context.Context, sim Simulator, id string) (*Room, error) {
	info, err := sim.CreateWorld(ctx, id, time.Now().UnixNano()&0x7fffffff)
	if err != nil {
		return nil, fmt.Errorf("create world: %w", err)
	}
	snap, err := sim.Snapshot(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("initial snapshot: %w", err)
	}
	r := &Room{ID: id, Desc: toDesc(info), sim: sim, subs: map[Subscriber]struct{}{},
		tracker: delta.NewTracker(), done: make(chan struct{})}
	r.last = toFrame(snap)
	r.tracker.Diff(r.last) // establish the baseline
	r.welcome, _ = json.Marshal(struct {
		Type      string `json:"type"`
		Aquarium  string `json:"aquariumId"`
		World     Desc   `json:"world"`
		ServerNow int64  `json:"serverTime"`
	}{"WELCOME", id, r.Desc, time.Now().UnixMilli()})
	return r, nil
}

func (r *Room) start(parent context.Context) {
	ctx, cancel := context.WithCancel(parent)
	r.cancel = cancel
	go r.run(ctx)
}

func (r *Room) run(ctx context.Context) {
	defer close(r.done)
	t := time.NewTicker(time.Second / time.Duration(r.Desc.TickRate))
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			r.tick(ctx)
		}
	}
}

func (r *Room) tick(ctx context.Context) {
	r.mu.Lock()
	idle := len(r.subs) == 0
	r.mu.Unlock()
	if idle { // nobody watching: pause until offline simulation exists (Phase 18)
		return
	}
	cctx, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
	snap, err := r.sim.Step(cctx, r.ID, 1)
	cancel()
	if err != nil {
		log.Printf("room %s: step failed: %v", r.ID, err)
		return
	}
	frame := toFrame(snap)
	r.mu.Lock()
	defer r.mu.Unlock()
	r.last = frame
	b, err := json.Marshal(r.tracker.Diff(frame))
	if err != nil {
		log.Printf("room %s: marshal: %v", r.ID, err)
		return
	}
	for s := range r.subs {
		if !s.Send(b) { // deltas are stateful, so a client that falls behind must resync by reconnecting
			delete(r.subs, s)
			go s.Close()
		}
	}
}

// Join registers s and queues WELCOME + a full SNAPSHOT before any delta can reach it.
func (r *Room) Join(s Subscriber) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	snap, _ := json.Marshal(delta.Snapshot(r.last))
	if !s.Send(r.welcome) || !s.Send(snap) {
		return false
	}
	r.subs[s] = struct{}{}
	return true
}

func (r *Room) Leave(s Subscriber) {
	r.mu.Lock()
	delete(r.subs, s)
	r.mu.Unlock()
}

func (r *Room) Viewers() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return len(r.subs)
}

func (r *Room) validSpecies(k string) bool {
	for _, s := range r.Desc.Species {
		if s.Key == k {
			return true
		}
	}
	return false
}

func clamp(v, lo, hi float32) float32 {
	if v != v { // NaN
		return lo
	}
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

// Feed drops food flakes. Coordinates are validated here and again by the simulation: never trust the client.
func (r *Room) Feed(ctx context.Context, x float32) error {
	_, err := r.sim.AddFood(ctx, r.ID, clamp(x, 20, r.Desc.Width-20), 30, 4)
	return err
}

func (r *Room) AddCreature(ctx context.Context, species string, x, y float32) error {
	if !r.validSpecies(species) {
		return errors.New("unknown species")
	}
	res, err := r.sim.AddCreature(ctx, r.ID, species, clamp(x, 20, r.Desc.Width-20), clamp(y, 20, r.Desc.FloorY-20))
	if err != nil {
		return err
	}
	if !res.Ok {
		return errors.New(res.Message)
	}
	return nil
}

// Inspect returns the serialized INSPECTION message for one creature, or nil if it no longer exists.
func (r *Room) Inspect(ctx context.Context, id int32) ([]byte, error) {
	d, err := r.sim.Inspect(ctx, r.ID, id)
	if err != nil || !d.Found {
		return nil, err
	}
	return json.Marshal(toInspection(d))
}

// Manager lazily creates rooms. Authentication, ownership and visits arrive in Phases 16-21.
type Manager struct {
	sim   Simulator
	mu    sync.Mutex
	rooms map[string]*Room
	ctx   context.Context
}

func NewManager(ctx context.Context, sim Simulator) *Manager {
	return &Manager{sim: sim, rooms: map[string]*Room{}, ctx: ctx}
}

func (m *Manager) Room(ctx context.Context, id string) (*Room, error) {
	if !ValidAquariumID(id) {
		return nil, errors.New("invalid aquarium id")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if r, ok := m.rooms[id]; ok {
		return r, nil
	}
	r, err := newRoom(ctx, m.sim, id)
	if err != nil {
		return nil, err
	}
	r.start(m.ctx)
	m.rooms[id] = r
	return r, nil
}

func (m *Manager) Shutdown() {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, r := range m.rooms {
		r.cancel()
		<-r.done
	}
}
