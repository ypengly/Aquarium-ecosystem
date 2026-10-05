package delta

import "testing"

func frame(tick int64, cs ...Creature) Frame { return Frame{Tick: tick, Creatures: cs} }

func TestDiffAddUpdateRemoveAndQuiet(t *testing.T) {
	tr := NewTracker()
	a := Creature{ID: 1, Species: "neon_tetra", X: 100, Y: 100, State: "EXPLORING", Energy: 80, Size: 14}
	b := Creature{ID: 2, Species: "oscar", X: 300, Y: 200, State: "RESTING", Energy: 60, Size: 38}

	m := tr.Diff(frame(1, a, b))
	if len(m.Added) != 2 || m.Added[0].Species == "" {
		t.Fatalf("first sight must send full creatures, got %+v", m)
	}

	m = tr.Diff(frame(2, a, b))
	if len(m.Added)+len(m.Updated)+len(m.Removed) != 0 {
		t.Fatalf("unchanged frame must produce an empty delta, got %+v", m)
	}

	a.X += 0.1 // below the 0.5px quantum: not worth sending
	m = tr.Diff(frame(3, a, b))
	if len(m.Updated) != 0 {
		t.Fatalf("sub-quantum motion should be suppressed")
	}

	a.X += 5
	a.State = "FLEEING"
	m = tr.Diff(frame(4, a, b))
	if len(m.Updated) != 1 || m.Updated[0].ID != 1 || m.Updated[0].Species != "" {
		t.Fatalf("expected one compact update for creature 1, got %+v", m)
	}

	m = tr.Diff(frame(5, a))
	if len(m.Removed) != 1 || m.Removed[0] != 2 {
		t.Fatalf("expected creature 2 removed, got %+v", m)
	}
}

func TestSnapshotDoesNotTouchBaseline(t *testing.T) {
	tr := NewTracker()
	f := frame(1, Creature{ID: 1, Species: "neon_tetra", X: 1, Y: 1})
	_ = Snapshot(f)
	if m := tr.Diff(f); len(m.Added) != 1 {
		t.Fatalf("baseline should be untouched by Snapshot, got %+v", m)
	}
}

func TestFoodLifecycle(t *testing.T) {
	tr := NewTracker()
	f := Frame{Tick: 1, Food: []Food{{ID: 9, Kind: "fish_food", X: 10, Y: 10}}}
	if m := tr.Diff(f); len(m.FoodAdded) != 1 {
		t.Fatal("food should be added")
	}
	f.Food[0].Y += 3
	if m := tr.Diff(f); len(m.FoodMoved) != 1 || m.FoodMoved[0].Kind != "" {
		t.Fatal("sinking food should produce a compact move")
	}
	if m := tr.Diff(Frame{Tick: 3}); len(m.FoodRemoved) != 1 {
		t.Fatal("eaten food should be removed")
	}
}
