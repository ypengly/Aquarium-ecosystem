// Package websocket upgrades HTTP connections and bridges them to a world.Room.
package websocket

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	gws "github.com/gorilla/websocket"

	"aquarium/server/internal/world"
)

const (
	writeWait   = 5 * time.Second
	pongWait    = 30 * time.Second
	pingEvery   = 20 * time.Second
	maxMsgBytes = 2048
	sendBuffer  = 32
)

// bucket is a small token-bucket rate limiter (one per connection).
type bucket struct {
	mu     sync.Mutex
	tokens float64
	last   time.Time
}

func (b *bucket) allow(cost float64) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	now := time.Now()
	b.tokens += now.Sub(b.last).Seconds() * 10 // refill 10 tokens/s
	if b.tokens > 20 {
		b.tokens = 20
	}
	b.last = now
	if b.tokens < cost {
		return false
	}
	b.tokens -= cost
	return true
}

type Client struct {
	conn  *gws.Conn
	room  *world.Room
	send  chan []byte
	done  chan struct{}
	once  sync.Once
	limit bucket
}

func (c *Client) Send(b []byte) bool {
	select {
	case <-c.done:
		return false
	default:
	}
	select {
	case c.send <- b:
		return true
	default:
		return false
	}
}

func (c *Client) Close() {
	c.once.Do(func() {
		close(c.done)
		_ = c.conn.Close()
	})
}

type inbound struct {
	Type    string  `json:"type"`
	X       float32 `json:"x"`
	Y       float32 `json:"y"`
	Species string  `json:"species"`
	ID      int32   `json:"id"`
}

func (c *Client) reply(kind, msg string) {
	b, _ := json.Marshal(map[string]string{"type": "ERROR", "code": kind, "message": msg})
	c.Send(b)
}

func (c *Client) readPump() {
	defer func() { c.room.Leave(c); c.Close() }()
	c.conn.SetReadLimit(maxMsgBytes)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error { return c.conn.SetReadDeadline(time.Now().Add(pongWait)) })
	for {
		_, data, err := c.conn.ReadMessage()
		if err != nil {
			return
		}
		var m inbound
		if json.Unmarshal(data, &m) != nil {
			c.reply("bad_message", "invalid JSON")
			continue
		}
		c.handle(m)
	}
}

func (c *Client) handle(m inbound) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	cost := map[string]float64{"FEED": 3, "ADD_CREATURE": 5, "INSPECT": 1}[m.Type]
	if cost == 0 {
		c.reply("unknown_type", "unknown message type")
		return
	}
	if !c.limit.allow(cost) {
		c.reply("rate_limited", "slow down")
		return
	}
	switch m.Type {
	case "FEED":
		if err := c.room.Feed(ctx, m.X); err != nil {
			c.reply("feed_failed", err.Error())
		}
	case "ADD_CREATURE":
		if err := c.room.AddCreature(ctx, m.Species, m.X, m.Y); err != nil {
			c.reply("add_failed", err.Error())
		}
	case "INSPECT":
		b, err := c.room.Inspect(ctx, m.ID)
		if err != nil {
			c.reply("inspect_failed", err.Error())
		} else if b != nil {
			c.Send(b)
		}
	}
}

func (c *Client) writePump() {
	t := time.NewTicker(pingEvery)
	defer func() { t.Stop(); c.Close() }()
	for {
		select {
		case <-c.done:
			return
		case b := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(gws.TextMessage, b); err != nil {
				return
			}
		case <-t.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(gws.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// originAllowed accepts same-host origins plus an explicit allow-list (ALLOWED_ORIGINS, comma separated).
func originAllowed(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true // non-browser clients
	}
	u, err := url.Parse(origin)
	if err != nil {
		return false
	}
	if strings.EqualFold(u.Host, r.Host) {
		return true
	}
	for _, o := range strings.Split(os.Getenv("ALLOWED_ORIGINS"), ",") {
		if o = strings.TrimSpace(o); o != "" && strings.EqualFold(o, origin) {
			return true
		}
	}
	return false
}

// Handler serves GET /ws?aquarium=<id>.
func Handler(m *world.Manager) http.HandlerFunc {
	up := gws.Upgrader{ReadBufferSize: 1024, WriteBufferSize: 16 * 1024, EnableCompression: true, CheckOrigin: originAllowed}
	return func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Query().Get("aquarium")
		if id == "" {
			id = "default"
		}
		if !world.ValidAquariumID(id) {
			http.Error(w, "invalid aquarium id", http.StatusBadRequest)
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
		room, err := m.Room(ctx, id)
		cancel()
		if err != nil {
			log.Printf("room %q unavailable: %v", id, err)
			http.Error(w, "aquarium unavailable", http.StatusServiceUnavailable)
			return
		}
		conn, err := up.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		conn.EnableWriteCompression(true)
		c := &Client{conn: conn, room: room, send: make(chan []byte, sendBuffer), done: make(chan struct{}),
			limit: bucket{tokens: 20, last: time.Now()}}
		go c.writePump()
		if !room.Join(c) {
			c.Close()
			return
		}
		c.readPump()
	}
}
