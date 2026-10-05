package world

import (
	"context"
	"encoding/json"
	"sync"
	"testing"

	"aquarium/server/internal/simpb"
)

type fakeSim struct {
	mu   sync.Mutex
	tick int64
}

func (f *fakeSim) CreateWorld(context.Context, string, int64) (*simpb.WorldInfo, error) {
	return &simpb.WorldInfo{Width: 1600, Height: 900, FloorY: 830, TickRate: 20,
		Species: []*simpb.SpeciesInfo{{Key: "neon_tetra", Name: "Neon Tetra"}}}, nil
}
func (f *fakeSim) snap() *simpb.Snapshot {
	return &simpb.Snapshot{Tick: f.tick, Creatures: []*simpb.CreatureState{{Id: 1, Species: "neon_tetra", X: float32(f.tick) * 3, Y: 10, State: "EXPLORING"}}}
}
func (f *fakeSim) Step(context.Context, string, int32) (*simpb.Snapshot, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.tick++
	return f.snap(), nil
}
func (f *fakeSim) Snapshot(context.Context, string) (*simpb.Snapshot, error) { return f.snap(), nil }
func (f *fakeSim) AddFood(context.Context, string, float32, float32, int32) (*simpb.CommandResult, error) {
	return &simpb.CommandResult{Ok: true}, nil
}
func (f *fakeSim) AddCreature(context.Context, string, string, float32, float32) (*simpb.CommandResult, error) {
	return &simpb.CommandResult{Ok: true}, nil
}
func (f *fakeSim) Inspect(context.Context, string, int32) (*simpb.CreatureDetail, error) {
	return &simpb.CreatureDetail{Found: false}, nil
}

type sub struct {
	msgs   [][]byte
	cap    int
	closed bool
}

func (s *sub) Send(b []byte) bool {
	if s.cap > 0 && len(s.msgs) >= s.cap {
		return false
	}
	s.msgs = append(s.msgs, b)
	return true
}
func (s *sub) Close() { s.closed = true }

func TestJoinSendsWelcomeThenSnapshotThenDeltas(t *testing.T) {
	ctx := context.Background()
	r, err := newRoom(ctx, &fakeSim{}, "t1")
	if err != nil {
		t.Fatal(err)
	}
	s := &sub{}
	if !r.Join(s) {
		t.Fatal("join failed")
	}
	r.tick(ctx)
	if len(s.msgs) != 3 {
		t.Fatalf("want welcome, snapshot, delta; got %d messages", len(s.msgs))
	}
	var types []string
	for _, b := range s.msgs {
		var h struct{ Type string }
		_ = json.Unmarshal(b, &h)
		types = append(types, h.Type)
	}
	if types[0] != "WELCOME" || types[1] != "SNAPSHOT" || types[2] != "DELTA" {
		t.Fatalf("unexpected order %v", types)
	}
}

func TestSlowSubscriberIsDropped(t *testing.T) {
	ctx := context.Background()
	r, _ := newRoom(ctx, &fakeSim{}, "t2")
	slow := &sub{cap: 3}
	r.Join(slow)
	r.tick(ctx)
	r.tick(ctx)
	if r.Viewers() != 0 {
		t.Fatal("slow subscriber should have been removed")
	}
}

func TestIdleRoomDoesNotStep(t *testing.T) {
	sim := &fakeSim{}
	r, _ := newRoom(context.Background(), sim, "t3")
	r.tick(context.Background())
	if sim.tick != 0 {
		t.Fatal("room with no viewers must not advance")
	}
}

func TestAquariumIDValidation(t *testing.T) {
	for id, want := range map[string]bool{"default": true, "my-tank_1": true, "": false, "../etc": false, "A": false} {
		if ValidAquariumID(id) != want {
			t.Errorf("%q: want %v", id, want)
		}
	}
}

func TestRoomRejectsUnknownSpecies(t *testing.T) {
	r, _ := newRoom(context.Background(), &fakeSim{}, "t4")
	if err := r.AddCreature(context.Background(), "kraken", 1, 1); err == nil {
		t.Fatal("expected error")
	}
	if err := r.AddCreature(context.Background(), "neon_tetra", 1, 1); err != nil {
		t.Fatal(err)
	}
}
