package world

import (
	"math"

	"aquarium/server/internal/delta"
	"aquarium/server/internal/simpb"
)

type Circle struct {
	X float32 `json:"x"`
	Y float32 `json:"y"`
	R float32 `json:"r"`
}

type SpeciesDesc struct {
	Key     string  `json:"key"`
	Name    string  `json:"name"`
	Size    float32 `json:"size"`
	Vision  float32 `json:"vision"`
	Color   uint32  `json:"color"`
	Stripe  uint32  `json:"stripe"`
	Trophic string  `json:"trophic"`
}

// Desc is the static description of an aquarium, sent once in WELCOME.
type Desc struct {
	Width    float32       `json:"width"`
	Height   float32       `json:"height"`
	FloorY   float32       `json:"floorY"`
	TickRate int32         `json:"tickRate"`
	Rocks    []Circle      `json:"rocks"`
	Shelters []Circle      `json:"shelters"`
	Species  []SpeciesDesc `json:"species"`
}

func toDesc(w *simpb.WorldInfo) Desc {
	d := Desc{Width: w.Width, Height: w.Height, FloorY: w.FloorY, TickRate: w.TickRate}
	for _, r := range w.Rocks {
		d.Rocks = append(d.Rocks, Circle{r.X, r.Y, r.R})
	}
	for _, s := range w.Shelters {
		d.Shelters = append(d.Shelters, Circle{s.X, s.Y, s.R})
	}
	for _, s := range w.Species {
		d.Species = append(d.Species, SpeciesDesc{s.Key, s.Name, s.Size, s.Vision, s.Color, s.Stripe, s.Trophic})
	}
	if d.TickRate <= 0 {
		d.TickRate = 20
	}
	return d
}

func pct(v float32) int { return int(math.Round(float64(v) * 100)) }

func toFrame(s *simpb.Snapshot) delta.Frame {
	f := delta.Frame{Tick: s.Tick, Time: s.Time}
	f.Creatures = make([]delta.Creature, 0, len(s.Creatures))
	for _, c := range s.Creatures {
		f.Creatures = append(f.Creatures, delta.Creature{
			ID: c.Id, Species: c.Species, X: c.X, Y: c.Y, Heading: c.Heading,
			State: c.State, Energy: pct(c.Energy), Hunger: pct(c.Hunger), Size: c.Size,
		})
	}
	for _, fd := range s.Food {
		f.Food = append(f.Food, delta.Food{ID: fd.Id, Kind: fd.Kind, X: fd.X, Y: fd.Y})
	}
	for _, e := range s.Events {
		f.Events = append(f.Events, delta.Event{Tick: e.Tick, Kind: e.Kind, Text: e.Text, CreatureID: e.CreatureId})
	}
	if s.Stats != nil {
		f.Stats = delta.Stats{StepMs: s.Stats.StepMs, Decisions: s.Stats.Decisions,
			Creatures: s.Stats.Creatures, Food: s.Stats.Food}
	}
	return f
}

type ActionScore struct {
	Action string  `json:"action"`
	Score  float32 `json:"score"`
}

type MemoryItem struct {
	Kind     string  `json:"kind"`
	X        float32 `json:"x"`
	Y        float32 `json:"y"`
	Strength float32 `json:"strength"`
}

// Inspection is the creature inspector + AI visualizer payload.
type Inspection struct {
	Type        string             `json:"type"`
	ID          int32              `json:"id"`
	Name        string             `json:"name"`
	Species     string             `json:"species"`
	Age         float64            `json:"age"`
	Health      float32            `json:"health"`
	Energy      float32            `json:"energy"`
	Hunger      float32            `json:"hunger"`
	Safety      float32            `json:"safety"`
	Social      float32            `json:"social"`
	Personality string             `json:"personality"`
	Mood        string             `json:"mood"`
	State       string             `json:"state"`
	Goal        string             `json:"goal"`
	Genes       map[string]float32 `json:"genes"`
	Traits      map[string]float32 `json:"traits"`
	Scores      []ActionScore      `json:"scores"`
	Memories    []MemoryItem       `json:"memories"`
	Recent      []string           `json:"recent"`
	Target      *Circle            `json:"target,omitempty"`
	Vision      float32            `json:"vision"`
}

func toInspection(d *simpb.CreatureDetail) *Inspection {
	in := &Inspection{
		Type: "INSPECTION", ID: d.Id, Name: d.Name, Species: d.Species, Age: d.Age, Health: d.Health,
		Energy: d.Energy, Hunger: d.Hunger, Safety: d.Safety, Social: d.Social, Personality: d.Personality,
		Mood: d.Mood, State: d.State, Goal: d.Goal, Genes: d.Genes, Traits: d.Traits, Recent: d.Recent,
		Vision: d.Vision,
	}
	for _, s := range d.Scores {
		in.Scores = append(in.Scores, ActionScore{s.Action, s.Score})
	}
	for _, m := range d.Memories {
		in.Memories = append(in.Memories, MemoryItem{m.Kind, m.X, m.Y, m.Strength})
	}
	if d.HasTarget {
		in.Target = &Circle{X: d.TargetX, Y: d.TargetY}
	}
	return in
}
