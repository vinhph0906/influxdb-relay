package metric

import (
	"context"
	"net/http"
	"time"

	ocprom "contrib.go.opencensus.io/exporter/prometheus"
	"github.com/prometheus/client_golang/prometheus"
	"go.opencensus.io/plugin/ochttp"
	"go.opencensus.io/stats/view"
)

const (
	defaultAddr              = ":8088"
	defaultShutdownTimeoutMs = 5000
)

// Server represents a metric server serves /metrics endpoint
type Server struct {
	h  *http.Server
	pe *ocprom.Exporter
}

// Run launchs the metric server
func (s *Server) Run() error {
	mux := http.NewServeMux()
	mux.Handle("/metrics", s.pe)

	s.h.Handler = mux
	if err := s.h.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

// Stop stops the metric server gracefully
func (s *Server) Stop() error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond*defaultShutdownTimeoutMs)
	defer cancel()
	return s.h.Shutdown(ctx)
}

// NewServer returns a metric server
func NewServer() (*Server, error) {
	promExporter, err := ocprom.NewExporter(
		ocprom.Options{
			Registerer: prometheus.DefaultRegisterer,
			Gatherer:   prometheus.DefaultGatherer,
		})
	if err != nil {
		return nil, err
	}
	view.RegisterExporter(promExporter)

	return &Server{
		h:  &http.Server{Addr: defaultAddr},
		pe: promExporter,
	}, nil
}

// HTTPHandler returns a http.Handler wrapper that instruments given HTTP server's handler
func HTTPHandler(h http.Handler) http.Handler {
	return &ochttp.Handler{
		Handler: h,
	}
}

// HTTPTransport returns a http.RoundTripper wrapper that instruments all outgoing requests from base
func HTTPTransport(base *http.Transport) http.RoundTripper {
	return &ochttp.Transport{
		Base: base,
	}
}
