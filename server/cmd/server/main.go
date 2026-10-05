package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"aquarium/server/internal/simclient"
	"aquarium/server/internal/websocket"
	"aquarium/server/internal/world"
)

func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	sim, err := simclient.Dial(env("SIM_ADDR", "localhost:50051"))
	if err != nil {
		log.Fatalf("dial simulation service: %v", err)
	}
	defer sim.Close()

	mgr := world.NewManager(ctx, sim)
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", websocket.Handler(mgr))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("ok")) })

	srv := &http.Server{Addr: ":" + env("PORT", "8080"), Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() {
		<-ctx.Done()
		shut, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shut)
	}()
	log.Printf("world server listening on %s", srv.Addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	mgr.Shutdown()
}
