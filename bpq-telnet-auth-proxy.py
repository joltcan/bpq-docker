#!/usr/bin/env python3
"""
bpq-telnet-auth-proxy.py - A simple Telnet proxy for BPQ that requires authentication

config.ini:

```ini
Config file:
[proxy]
port = 8773
user_file = users.csv
destination_host = <bpq host/ip>
destination_port = 8772
```

users.csv:

```csv
"Callsign","Password"
```

"""
import asyncio
import configparser
import csv

# Load config
def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
        "proxy_port": int(config.get("proxy", "port", fallback=8773)),
        "user_file": config.get("proxy", "user_file", fallback="users.csv"),
        "destination_host": config.get("proxy", "destination_host", fallback="127.0.0.1"),
        "destination_port": int(config.get("proxy", "destination_port", fallback=8772)),
    }

# Load users from CSV file
def load_users(filename):
    users = {}
    try:
        with open(filename, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 2:
                    users[row[0]] = row[1]  # userid -> password
    except FileNotFoundError:
        print("User file not found!")
    return users

async def handle_client(client_reader, client_writer):
    config = load_config()
    users = load_users(config["user_file"])
    addr = client_writer.get_extra_info("peername")
    print(f"Connection from {addr}")

    try:
        # Connect to BPQ immediately
        destination_host = config["destination_host"]
        destination_port = config["destination_port"]
        print(f"Connecting to BPQ at {destination_host}:{destination_port}")
        bpq_reader, bpq_writer = await asyncio.open_connection(destination_host, destination_port)

        callsign = None
        authenticated = False
        password_prompted = False

        # Log everything the client sends before BPQ asks for Callsign
        async def log_client_input():
            nonlocal callsign, authenticated, password_prompted

            while not client_reader.at_eof():
                data = await client_reader.read(1024)
                if not data:
                    break
                decoded_data = data.decode(errors='ignore').strip()
                #print(f"Client Sent: {decoded_data}")

                 # If we haven't yet captured the callsign, assume the first message is it
                if not callsign:
                    callsign = decoded_data
                    print(f"Captured Callsign: {callsign}")

                # If BPQ already prompted for a password, capture and validate it
                if callsign and password_prompted and not authenticated:
                    #print(f"Processing Password: {decoded_data}")
                    password = decoded_data

                    # Validate password
                    if callsign in users and users[callsign] == password:
                        print(f"Authentication successful for {callsign}")
                        authenticated = True
                    else:
                        print(f"Authentication failed for {callsign}, disconnecting client")
                        client_writer.write(b"ERROR: Authentication Failed\n")
                        await client_writer.drain()
                        client_writer.close()
                        await client_writer.wait_closed()
                        return

                # Forward client data to BPQ
                bpq_writer.write(data)
                await bpq_writer.drain()

        # Start forwarding BPQ data to client and log responses
        async def forward_bpq_to_client():
            nonlocal password_prompted
            while not bpq_reader.at_eof():
                try:
                    chunk = await bpq_reader.read(1024)
                    if not chunk:
                        break
                    decoded_chunk = chunk.decode(errors='ignore').strip()
                    #print(f"BPQ Response: {decoded_chunk}")
                    client_writer.write(chunk)
                    await client_writer.drain()

                    # Detect when BPQ asks for the password
                    if "Password :" in decoded_chunk and not password_prompted:
                        password_prompted = True
                except Exception as e:
                    print(f"Error forwarding BPQ data: {e}")
                    break

        # Start tasks
        await asyncio.gather(
            forward_bpq_to_client(),
            log_client_input()
        )

        # Close BPQ connection
        bpq_writer.close()
        await bpq_writer.wait_closed()

    except Exception as e:
        print(f"Error: {e}")

    client_writer.close()
    await client_writer.wait_closed()

async def main():
    config = load_config()
    server = await asyncio.start_server(handle_client, "0.0.0.0", config["proxy_port"])
    addr = server.sockets[0].getsockname()
    print(f"Proxy running on {addr}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())