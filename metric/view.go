package metric

import (
	"go.opencensus.io/plugin/ochttp"
	"go.opencensus.io/stats/view"
	"go.opencensus.io/tag"
)

var (
	defaultSizeDistribution    = view.Distribution(1024, 2048, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456, 1073741824, 4294967296)
	defaultLatencyDistribution = view.Distribution(1, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200, 250, 300, 400, 500, 650, 800, 1000, 2000, 5000, 10000, 20000)
)

var (
	httpViews = []*view.View{
		&view.View{
			Name:        "relay/http/request_count",
			Description: "Count of HTTP requests started",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerRequestCount,
			Aggregation: view.Count(),
		},
		&view.View{
			Name:        "relay/http/request_bytes",
			Description: "Size distribution of HTTP request body",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerRequestBytes,
			Aggregation: defaultSizeDistribution,
		},
		&view.View{
			Name:        "relay/http/response_bytes",
			Description: "Size distribution of HTTP response body",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerResponseBytes,
			Aggregation: defaultSizeDistribution,
		},
		&view.View{
			Name:        "relay/http/latency",
			Description: "Latency distribution of HTTP requests",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerLatency,
			Aggregation: defaultLatencyDistribution,
		},
		&view.View{
			Name:        "relay/http/request_count_by_method",
			Description: "Server request count by HTTP method",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerRequestCount,
			Aggregation: view.Count(),
		},
		&view.View{
			Name:        "relay/http/response_count_by_status_code",
			Description: "Server response count by status code",
			TagKeys:     []tag.Key{ochttp.Path, ochttp.Method, ochttp.StatusCode},
			Measure:     ochttp.ServerLatency,
			Aggregation: view.Count(),
		},
	}

	httpOutputViews = []*view.View{
		&view.View{
			Name:        "relay/http/output/sent_bytes",
			Description: "Total bytes sent in request body (not including headers), by HTTP method and response status",
			TagKeys:     []tag.Key{ochttp.KeyClientHost, ochttp.KeyClientPath, ochttp.KeyClientMethod, ochttp.KeyClientStatus},
			Measure:     ochttp.ClientSentBytes,
			Aggregation: defaultSizeDistribution,
		},
		&view.View{
			Name:        "relay/http/output/received_bytes",
			Description: "Total bytes received in response bodies (not including headers but including error responses with bodies), by HTTP method and response status",
			TagKeys:     []tag.Key{ochttp.KeyClientHost, ochttp.KeyClientPath, ochttp.KeyClientMethod, ochttp.KeyClientStatus},
			Measure:     ochttp.ClientReceivedBytes,
			Aggregation: defaultSizeDistribution,
		},
		&view.View{
			Name:        "relay/http/output/latency",
			Description: "End-to-end latency, by HTTP method and response status",
			TagKeys:     []tag.Key{ochttp.KeyClientHost, ochttp.KeyClientPath, ochttp.KeyClientMethod, ochttp.KeyClientStatus},
			Measure:     ochttp.ClientRoundtripLatency,
			Aggregation: defaultSizeDistribution,
		},
		&view.View{
			Name:        "relay/http/output/completed_count",
			Description: "Count of completed requests, by HTTP method and response status",
			TagKeys:     []tag.Key{ochttp.KeyClientHost, ochttp.KeyClientPath, ochttp.KeyClientMethod, ochttp.KeyClientStatus},
			Measure:     ochttp.ClientRoundtripLatency,
			Aggregation: view.Count(),
		},
	}
)

func init() {
	view.Register(httpViews...)
	view.Register(httpOutputViews...)
}
