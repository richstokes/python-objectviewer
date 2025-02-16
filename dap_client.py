import socket
import json

HOST = "127.0.0.1"
PORT = 5678
DEPTH_LIMIT = 1  # 2  # How many levels deep to fetch variables


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

    length_str = headers.get("content-length")
    if not length_str:
        raise ConnectionError("No Content-Length header in DAP message.")

    length = int(length_str)
    raw_json = read_exactly(sock, length)
    return json.loads(raw_json.decode("utf-8"))


def send_dap_request(sock, seq, command, arguments=None):
    """Sends a DAP request. Returns the new seq (seq+1)."""
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


def fetch_variables(sock, seq, var_ref):
    """
    Fetches the immediate children for the given variablesReference (single DAP "variables" request).
    Returns (updated_seq, list_of_variable_dicts).
    """
    seq = send_dap_request(sock, seq, "variables", {"variablesReference": var_ref})

    variables_response = None
    while variables_response is None:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "variables":
            variables_response = msg
        else:
            # Just log and continue
            print("Got message (waiting for variables):", msg)

    vars_body = variables_response.get("body", {})
    variables_list = vars_body.get("variables", [])
    return seq, variables_list


def fetch_variable_tree(sock, seq, var_ref, depth=DEPTH_LIMIT, visited=None):
    """
    Recursively fetches a tree of variables up to a certain depth.
    - var_ref: The DAP variablesReference to expand.
    - depth: How many levels deep to recurse.
    - visited: A set of references we've already expanded, to avoid cycles.

    Returns (updated_seq, list_of_trees).

    Each item in list_of_trees is a dict:
    {
      "name": str,
      "value": str,
      "type": str,
      "evaluateName": str or None,
      "variablesReference": int,
      "children": [ ... nested items ... ]
    }
    """
    if visited is None:
        visited = set()

    # If we've already visited this reference, skip to avoid infinite loop
    if var_ref in visited:
        return seq, [
            {"name": "<recursive>", "value": "...", "type": "recursive", "children": []}
        ]

    visited.add(var_ref)

    # Always do a single-level "variables" fetch
    seq, vars_list = fetch_variables(sock, seq, var_ref)

    result = []
    for v in vars_list:
        child = {
            "name": v["name"],
            "value": v.get("value", ""),
            "type": v.get("type", ""),
            "evaluateName": v.get("evaluateName"),
            "variablesReference": v.get("variablesReference", 0),
            "children": [],
        }

        # If this variable has nested children, and we still have depth left
        child_ref = child["variablesReference"]
        if child_ref and child_ref > 0 and depth > 0:
            # Recursively fetch child variables
            seq, child_vars = fetch_variable_tree(
                sock, seq, child_ref, depth=depth - 1, visited=visited
            )
            child["children"] = child_vars

        result.append(child)

    return seq, result


def dap_client():
    """Example DAP client that pauses the main thread and fetches local/global variables with children."""
    print(f"Connecting to {HOST}:{PORT}...")
    sock = socket.create_connection((HOST, PORT))
    sock.settimeout(10.0)

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

    # 4) threads
    seq = send_dap_request(sock, seq, "threads")
    print("Sent 'threads' request.")

    threads_response = None
    while not threads_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "threads":
            threads_response = msg
        else:
            print("Got message (waiting for threads):", msg)

    threads_body = threads_response["body"]
    threads_list = threads_body.get("threads", [])
    print(f"Threads: {threads_list}")

    if not threads_list:
        print("No threads. Exiting.")
        sock.close()
        return {}

    # Pause the first thread so we can inspect variables
    thread_id = threads_list[0]["id"]
    print(f"Pausing thread {thread_id}...")

    seq = send_dap_request(sock, seq, "pause", {"threadId": thread_id})
    paused = False
    while not paused:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "pause":
            print("Got 'pause' response, success:", msg.get("success"))
        elif msg.get("type") == "event" and msg.get("event") == "stopped":
            reason = msg["body"].get("reason")
            print(f"Thread is now paused (reason: {reason})")
            paused = True
        else:
            print("Got message while waiting to pause:", msg)

    # Now that thread is paused, ask for "stackTrace"
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
    print(f"Found {len(frames)} frames.")

    globals_result = []
    locals_result = []

    # Inspect the top frame's scopes, or all frames if you like
    for f in frames:
        frame_id = f["id"]
        print(
            f"Frame ID {frame_id}: {f['name']} @ {f.get('source',{}).get('path','no_source')}"
        )

        # 1) get scopes
        seq = send_dap_request(sock, seq, "scopes", {"frameId": frame_id})
        scopes_response = None
        while not scopes_response:
            msg = read_dap_message(sock)
            if msg.get("type") == "response" and msg.get("command") == "scopes":
                scopes_response = msg
            else:
                print("Got message (waiting for scopes):", msg)

        scope_list = scopes_response["body"].get("scopes", [])
        for scope_info in scope_list:
            scope_name = scope_info["name"]
            scope_ref = scope_info["variablesReference"]
            print(f"  Scope: {scope_name} (ref={scope_ref})")

            # 2) Recursively expand the variables in this scope
            seq, var_tree = fetch_variable_tree(sock, seq, scope_ref, depth=2)

            if scope_name.lower() == "locals":
                locals_result.extend(var_tree)
            elif scope_name.lower() == "globals":
                globals_result.extend(var_tree)
            else:
                print(f"    (Scope '{scope_name}' not recognized as locals/globals)")

    print("Done collecting variables. Closing socket.")
    sock.close()

    return {
        "globals": globals_result,
        "locals": locals_result,
    }


if __name__ == "__main__":
    result = dap_client()
    print("\n=== Final Expanded Variables ===\n")
    print(json.dumps(result, indent=2))
