# Not part of upstream Garden: node_stdlib with an official release binary
# instead of a source build, so a Node/llhttp reference is available quickly.
FROM http-garden-soil:latest
ARG NODE_VERSION=v26.13.0
ARG NODE_SHA256=d28a96af6c38596f6d9d97c0ee531c13d238d757742387d1928de822d959e997
RUN apt -y update && apt -y install --no-install-recommends curl xz-utils \
 && curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz" -o /node.tar.xz \
 && echo "${NODE_SHA256}  /node.tar.xz" | sha256sum -c - \
 && mkdir /node && tar -xJf /node.tar.xz -C /node --strip-components=1 && rm /node.tar.xz
COPY app.js /app/app.js
CMD ["/node/bin/node", "app.js"]
