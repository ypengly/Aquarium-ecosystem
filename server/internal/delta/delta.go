// Package delta turns full simulation frames into compact wire messages.
// Only creatures whose quantised state changed are sent; removals are explicit.
package delta

import "math"

type Creature struct {
	ID      int32   `json:"i"`
	Species string  `json:"sp,omitempty"` // only on first sight
	X       float32 `json:"x"`
	Y       float32 `json:"y"`
	Heading float32 `json:"h"`
	State   string  `json:"s"`
	Energy  int     `json:"e"`  // percent
	Hunger  int     `json:"hu"` // percent
	Size    float32 `json:"z,omitempty"`
}

type Food struct {
	ID   int32   `json:"i"`
	Kind string  `json:"k,omitempty"`
	X    float32 `json:"x"`
	Y    float32 `json:"y"`
}

type Event struct {
	Tick       int64  `json:"tick"`
	Kind       string `json:"kind"`
	Text       string `json:"text"`
	CreatureID int32  `json:"creatureId"`
}

type Stats struct {
	StepMs    float32 `json:"stepMs"`
	Decisions int32   `json:"decisions"`
	Creatures int32   `json:"creatures"`
	Food      int32   `json:"food"`
}

// Frame is one full simulation state.
type Frame struct {
	Tick      int64
	Time      float64
	Creatures []Creature
	Food      []Food
	Events    []Event
	Stats     Stats
}

// Message is what goes over the wire ("SNAPSHOT" on join, "DELTA" every tick afterwards).
type Message struct {
	Type        string     `json:"type"`
	Tick        int64      `json:"tick"`
	Time        float64    `json:"time"`
	Added       []Creature `json:"add,omitempty"`
	Updated     []Creature `json:"upd,omitempty"`
	Removed     []int32    `json:"rem,omitempty"`
	FoodAdded   []Food     `json:"fadd,omitempty"`
	FoodMoved   []Food     `json:"fupd,omitempty"`
	FoodRemoved []int32    `json:"frem,omitempty"`
	Events      []Event    `json:"events,omitempty"`
	Stats       *Stats     `json:"stats,omitempty"`
}

type quant struct {
	x, y, h int32
	s       string
	e, hu   int
}

func qc(c Creature) quant {
	return quant{
		x: int32(math.Round(float64(c.X) * 2)), // 0.5 px
		y: int32(math.Round(float64(c.Y) * 2)),
		h: int32(math.Round(float64(c.Heading) * 20)), // ~3 degrees
		s: c.State, e: c.Energy, hu: c.Hunger,
	}
}

type fq struct{ x, y int32 }

func qf(f Food) fq {
	return fq{int32(math.Round(float64(f.X) * 2)), int32(math.Round(float64(f.Y) * 2))}
}

// Tracker remembers what clients of one room have already been told.
type Tracker struct {
	creatures map[int32]quant
	food      map[int32]fq
}

func NewTracker() *Tracker {
	return &Tracker{creatures: map[int32]quant{}, food: map[int32]fq{}}
}

// Diff computes the delta against the baseline and advances the baseline.
func (t *Tracker) Diff(f Frame) Message {
	m := Message{Type: "DELTA", Tick: f.Tick, Time: f.Time, Events: f.Events, Stats: &f.Stats}
	seen := make(map[int32]struct{}, len(f.Creatures))
	for _, c := range f.Creatures {
		seen[c.ID] = struct{}{}
		q := qc(c)
		old, known := t.creatures[c.ID]
		switch {
		case !known:
			m.Added = append(m.Added, c)
		case old != q:
			c.Species, c.Size = "", 0
			m.Updated = append(m.Updated, c)
		default:
			continue
		}
		t.creatures[c.ID] = q
	}
	for id := range t.creatures {
		if _, ok := seen[id]; !ok {
			m.Removed = append(m.Removed, id)
			delete(t.creatures, id)
		}
	}
	seenF := make(map[int32]struct{}, len(f.Food))
	for _, fd := range f.Food {
		seenF[fd.ID] = struct{}{}
		q := qf(fd)
		old, known := t.food[fd.ID]
		switch {
		case !known:
			m.FoodAdded = append(m.FoodAdded, fd)
		case old != q:
			fd.Kind = ""
			m.FoodMoved = append(m.FoodMoved, fd)
		default:
			continue
		}
		t.food[fd.ID] = q
	}
	for id := range t.food {
		if _, ok := seenF[id]; !ok {
			m.FoodRemoved = append(m.FoodRemoved, id)
			delete(t.food, id)
		}
	}
	return m
}

// Snapshot is a full message for a joining client. It does not touch any baseline.
func Snapshot(f Frame) Message {
	return Message{Type: "SNAPSHOT", Tick: f.Tick, Time: f.Time, Added: f.Creatures, FoodAdded: f.Food, Stats: &f.Stats}
}
