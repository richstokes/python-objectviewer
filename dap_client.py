#!/usr/bin/env python3

import socket
import json

HOST = "127.0.0.1"
PORT = 5678


def read_line(sock):
    """Reads a single line (terminated by \n) from the socket, stripping \r\n."""
    buf = []
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Socket closed while reading line.")
        if chunk == b"\n":
            break
        buf.append(chunk)
    line = b"".join(buf).rstrip(b"\r")
    return line.decode("utf-8")


def read_exactly(sock, n):
    """Reads exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed unexpectedly.")
        data += chunk
    return data


def read_dap_message(sock):
    """
    Reads and returns one DAP message from the socket as a Python dict.
    Raises ConnectionError if the socket is closed or data is invalid.
    """
    # Read headers until blank line
    headers = {}
    while True:
        line = read_line(sock)
        if line == "":
            # Empty line -> end of headers
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    # Must have Content-Length
    length_str = headers.get("content-length")
    if not length_str:
        raise ConnectionError("No Content-Length header received; invalid DAP message.")

    length = int(length_str)
    raw_json = read_exactly(sock, length)
    return json.loads(raw_json.decode("utf-8"))


def send_dap_request(sock, seq, command, arguments=None):
    """
    Sends a DAP request. Returns new seq (seq+1).
    """
    if arguments is None:
        arguments = {}

    request = {
        "seq": seq,
        "type": "request",
        "command": command,
        "arguments": arguments,
    }
    payload = json.dumps(request).encode("utf-8")
    header = f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
    sock.sendall(header + payload)
    return seq + 1


def dap_client():
    print(f"Connecting to {HOST}:{PORT}...")
    sock = socket.create_connection((HOST, PORT))
    sock.settimeout(10.0)  # Adjust or remove timeout as needed

    seq = 1

    # 1) initialize
    seq = send_dap_request(
        sock,
        seq,
        "initialize",
        {
            "adapterID": "debugpy-test",
            "pathFormat": "path",
            "linesStartAt1": True,
            "columnsStartAt1": True,
            "supportsVariableType": True,
            "supportsVariablePaging": True,
            "supportsRunInTerminalRequest": False,
        },
    )
    print("Sent 'initialize' request.")

    # Wait for initialize response
    initialize_response = None
    while not initialize_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "initialize":
            initialize_response = msg
            print("Got 'initialize' response, success:", msg.get("success"))
        else:
            print("Got message (before initialize response):", msg)

    # 2) attach
    seq = send_dap_request(sock, seq, "attach", {"subProcess": False})
    print("Sent 'attach' request.")

    # 3) configurationDone
    print("Sending 'configurationDone' request...")
    seq = send_dap_request(sock, seq, "configurationDone")
    print("Sent 'configurationDone' request.")

    config_done_response = None
    while not config_done_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "configurationDone":
            config_done_response = msg
            print("Got 'configurationDone' response, success:", msg.get("success"))
        else:
            print("Got message (waiting for configurationDone):", msg)

    # 4) request threads
    seq = send_dap_request(sock, seq, "threads")
    print("Sent 'threads' request.")

    threads_response = None
    while not threads_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "threads":
            threads_response = msg
        else:
            print("Got message (waiting for threads):", msg)

    threads = threads_response["body"]["threads"]
    print(f"Threads: {threads}")

    if not threads:
        print("No threads to pause. Exiting.")
        sock.close()
        return

    # 5) Pause the first thread
    thread_id = threads[0]["id"]
    print(f"Pausing thread {thread_id}...")

    seq = send_dap_request(sock, seq, "pause", {"threadId": thread_id})

    paused = False
    while not paused:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "pause":
            print("Got 'pause' response, success:", msg.get("success"))
            # We expect a subsequent "stopped" event to confirm the thread is paused
        elif msg.get("type") == "event" and msg.get("event") == "stopped":
            # The thread is now paused
            reason = msg["body"].get("reason")
            print(f"Thread is stopped, reason: {reason}")
            paused = True
        else:
            print("Got message while waiting for pause:", msg)

    # 6) Now we can get fresh threads again (the same ID is fine, but let's be sure)
    seq = send_dap_request(sock, seq, "threads")
    threads_again_response = None
    while not threads_again_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "threads":
            threads_again_response = msg
        else:
            print("Got message (waiting for threads again):", msg)

    # 7) Get stack trace of the paused thread
    # (We assume the same thread ID, but you could re-lookup in case new threads started)
    print(f"\nRequesting stack trace for thread {thread_id} (paused).")
    seq = send_dap_request(
        sock, seq, "stackTrace", {"threadId": thread_id, "startFrame": 0, "levels": 20}
    )

    stack_trace_response = None
    while not stack_trace_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "stackTrace":
            stack_trace_response = msg
        else:
            print("Got message (waiting for stackTrace):", msg)

    frames = stack_trace_response["body"].get("stackFrames", [])
    global_variables = []
    local_variables = []

    for frame in frames:
        frame_id = frame["id"]
        print(
            f"  Frame {frame_id}: {frame['name']} ({frame.get('source', {}).get('path', 'no_source')})"
        )

        # Get scopes in the paused frame
        seq = send_dap_request(sock, seq, "scopes", {"frameId": frame_id})
        scopes_response = None
        while not scopes_response:
            msg = read_dap_message(sock)
            if msg.get("type") == "response" and msg.get("command") == "scopes":
                scopes_response = msg
            else:
                print("Got message (waiting for scopes):", msg)

        all_scopes = scopes_response["body"].get("scopes", [])
        for scope in all_scopes:
            scope_name = scope["name"]
            var_ref = scope["variablesReference"]
            print(f"    Scope: {scope_name} (variablesReference={var_ref})")

            # Get variables in this scope
            seq = send_dap_request(
                sock, seq, "variables", {"variablesReference": var_ref}
            )
            variables_response = None
            while variables_response is None:
                msg = read_dap_message(sock)
                if msg.get("type") == "response" and msg.get("command") == "variables":
                    variables_response = msg
                else:
                    print("Got message (waiting for variables):", msg)

            vars_body = variables_response.get("body", {})
            variables_list = vars_body.get("variables", [])
            if not variables_list:
                print("      No variables found in this scope or an error occurred.")
                continue

            for v in variables_list:
                # print(f"DEBUG v: \n{v}\n*****\n")
                name = v["name"]
                value = v["value"]
                var_type = v.get("type", "unknown")
                # print(f"      {name} = {value} (type={var_type})")

                if scope_name.lower() == "locals":
                    local_variables.append(
                        {
                            "name": name,
                            "value": value,
                            "type": var_type,
                            "evaluateName": v.get("evaluateName"),
                            "variablesReference": v.get("variablesReference"),
                        }
                    )
                elif scope_name.lower() == "globals":
                    global_variables.append(
                        {
                            "name": name,
                            "value": value,
                            "type": var_type,
                            "evaluateName": v.get("evaluateName"),
                            "variablesReference": v.get("variablesReference"),
                        }
                    )
                else:
                    print(f"      Unknown scope: {scope_name}")

    print("\nDone collecting variables. Closing socket.")
    sock.close()
    return {"globals": global_variables, "locals": local_variables}


if __name__ == "__main__":
    dap_client()
