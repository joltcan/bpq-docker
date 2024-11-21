FROM debian:stable-slim

# Update the package list and install necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget dbus libnss-nis libnss-nisplus libtirpc3  gosu\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /tmp

# Download LinBPQ64 binary
RUN wget https://www.cantab.net/users/john.wiseman/Downloads/Beta/linbpq64 && \
    chmod +x linbpq64 && mv linbpq64 /usr/local/bin

# Create an entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint to switch user
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["linbpq64"]