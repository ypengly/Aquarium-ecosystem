// Package simclient is the gRPC client for the Python simulation service.
package simclient

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"aquarium/server/internal/simpb"
)

type Client struct {
	conn *grpc.ClientConn
	c    simpb.SimulationClient
}

func Dial(addr string) (*Client, error) {
	conn, err := grpc.Dial(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, err
	}
	return &Client{conn: conn, c: simpb.NewSimulationClient(conn)}, nil
}

func (c *Client) Close() error { return c.conn.Close() }

func (c *Client) CreateWorld(ctx context.Context, id string, seed int64) (*simpb.WorldInfo, error) {
	return c.c.CreateWorld(ctx, &simpb.CreateWorldRequest{AquariumId: id, Seed: seed, PopulateDefault: true})
}

func (c *Client) Step(ctx context.Context, id string, ticks int32) (*simpb.Snapshot, error) {
	return c.c.Step(ctx, &simpb.StepRequest{AquariumId: id, Ticks: ticks})
}

func (c *Client) Snapshot(ctx context.Context, id string) (*simpb.Snapshot, error) {
	return c.c.GetSnapshot(ctx, &simpb.AquariumRef{AquariumId: id})
}

func (c *Client) AddFood(ctx context.Context, id string, x, y float32, count int32) (*simpb.CommandResult, error) {
	return c.c.AddFood(ctx, &simpb.AddFoodRequest{AquariumId: id, X: x, Y: y, Count: count, Kind: "fish_food"})
}

func (c *Client) AddCreature(ctx context.Context, id, species string, x, y float32) (*simpb.CommandResult, error) {
	return c.c.AddCreature(ctx, &simpb.AddCreatureRequest{AquariumId: id, Species: species, X: x, Y: y})
}

func (c *Client) Inspect(ctx context.Context, id string, creatureID int32) (*simpb.CreatureDetail, error) {
	return c.c.Inspect(ctx, &simpb.InspectRequest{AquariumId: id, CreatureId: creatureID})
}
