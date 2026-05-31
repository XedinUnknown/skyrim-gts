FROM mcr.microsoft.com/dotnet/sdk:8.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends make python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN mkdir -p /tmp/home/.config/opencode \
             /tmp/home/.local/share/opencode/repos \
             /tmp/home/.local/state \
             /tmp/home/.cache && \
    chmod 1777 /tmp/home /tmp/home/.config /tmp/home/.config/opencode \
               /tmp/home/.local /tmp/home/.local/share /tmp/home/.local/share/opencode \
               /tmp/home/.local/state /tmp/home/.cache

ENV DOTNET=/usr/bin/dotnet

CMD ["make", "help"]
