# The MIT License (MIT)
#
# Copyright (c) 2018 Vente-Privée
#
# Permission is hereby granted, free of  charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction,  including without limitation the rights
# to use,  copy, modify,  merge, publish,  distribute, sublicense,  and/or sell
# copies  of the  Software,  and to  permit  persons to  whom  the Software  is
# furnished to do so, subject to the following conditions:
#
# The above  copyright notice and this  permission notice shall be  included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE  IS PROVIDED "AS IS",  WITHOUT WARRANTY OF ANY  KIND, EXPRESS OR
# IMPLIED,  INCLUDING BUT  NOT LIMITED  TO THE  WARRANTIES OF  MERCHANTABILITY,
# FITNESS FOR A  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO  EVENT SHALL THE
# AUTHORS  OR COPYRIGHT  HOLDERS  BE LIABLE  FOR ANY  CLAIM,  DAMAGES OR  OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

FROM golang:alpine as builder

# Add missing git
RUN apk --update add git build-base
WORKDIR $GOPATH/src/influxdb-relay/
COPY . .
# Install
RUN go get -d -v
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags='-w -s -extldflags "-static"' -o /go/bin/influxdb-relay

FROM scratch
# Copy our static executable.
COPY --from=builder /go/bin/influxdb-relay /usr/bin/influxdb-relay

ENTRYPOINT [ "/usr/bin/influxdb-relay" ]

EXPOSE 9096

CMD ["-config", "/etc/influxdb-relay/influxdb-relay.conf" ]
# EOF
VOLUME ["/etc/influxdb-relay/influxdb-relay.conf"]