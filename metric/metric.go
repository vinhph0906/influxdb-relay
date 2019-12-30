package metric

import (
	"context"
	"net/http"
	"time"

	ocprom "contrib.go.opencensus.io/exporter/prometheus"
	"github.com/prometheus/client_golang/prometheus"
	"go.opencensus.io/plugin/ochttp"
	"go.opencensus.io/stats/view"
	"go.opencensus.io/tag"
)

const (
	defaultAddr              = ":8088"
	defaultShutdownTimeoutMs = 5000
)

type Server struct {
	h  *http.Server
	pe *ocprom.Exporter
}

func init() {
	registerDefaultServerViews()
	registerDefaultClientViews()
}

func (s *Server) Run() error {
	mux := http.NewServeMux()
	mux.Handle("/metrics", s.pe)

	s.h.Handler = mux
	if err := s.h.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

func (s *Server) Stop() error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Millisecond*defaultShutdownTimeoutMs)
	defer cancel()
	return s.h.Shutdown(ctx)
}

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

func HTTPHandler(h http.Handler) http.Handler {
	return &ochttp.Handler{
		Handler: h,
	}
}

func HTTPTransport(base *http.Transport) http.RoundTripper {
	return &ochttp.Transport{
		Base: base,
	}
}

func registerDefaultServerViews() {
	views := []*view.View{
		ochttp.ServerRequestCountView,
		ochttp.ServerRequestBytesView,
		ochttp.ServerResponseBytesView,
		ochttp.ServerLatencyView,
		ochttp.ServerRequestCountByMethod,
		ochttp.ServerResponseCountByStatusCode,
	}
	for _, view := range views {
		view.TagKeys = []tag.Key{
			ochttp.Path,
			ochttp.Method,
			ochttp.StatusCode,
		}
	}
	view.Register(views...)
}

func registerDefaultClientViews() {
	views := []*view.View{
		ochttp.ClientSentBytesDistribution,
		ochttp.ClientReceivedBytesDistribution,
		ochttp.ClientRoundtripLatencyDistribution,
		ochttp.ClientCompletedCount,
	}
	for _, view := range views {
		view.TagKeys = []tag.Key{
			ochttp.KeyClientHost,
			ochttp.KeyClientPath,
			ochttp.KeyClientMethod,
			ochttp.KeyClientStatus,
		}
	}
	view.Register(views...)
}
