FROM debian:trixie-slim AS build
RUN apt -y update && apt -y install --no-install-recommends ca-certificates curl xz-utils git
ARG ZIG_VERSION
RUN curl -fsSL "https://ziglang.org/download/${ZIG_VERSION}/zig-x86_64-linux-${ZIG_VERSION}.tar.xz" -o /zig.tar.xz \
 && mkdir /zig && tar -xJf /zig.tar.xz -C /zig --strip-components=1 && rm /zig.tar.xz

ARG APP_REPO
ARG APP_BRANCH
ARG APP_VERSION
RUN git clone --branch "$APP_BRANCH" "$APP_REPO" /src/dusty-src \
 && git -C /src/dusty-src checkout "$APP_VERSION"

COPY harness /src
RUN cd /src && /zig/zig build -Doptimize=ReleaseSafe

FROM debian:trixie-slim
WORKDIR /app
COPY --from=build /src/zig-out/bin/dusty-garden /app/dusty-garden
CMD ["/app/dusty-garden"]
