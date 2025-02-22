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
            print("Got message (waiting for variables):", msg)

    vars_body = variables_response.get("body", {})
    variables_list = vars_body.get("variables", [])
    return seq, variables_list


def fetch_variable_tree(sock, seq, var_ref, depth, visited=None):
    """
    Recursively fetches a tree of variables up to 'depth' levels.

    Each returned item is a dict:
    {
      "name": str,
      "value": str,
      "type": str,
      "evaluateName": str or None,
      "variablesReference": int,
      "children": [...]
    }
    """
    if visited is None:
        visited = set()

    # Prevent infinite recursion on cyclical references
    if var_ref in visited:
        return seq, [
            {
                "name": "<recursive>",
                "value": "...",
                "type": "recursive",
                "evaluateName": None,
                "variablesReference": 0,
                "children": [],
            }
        ]

    visited.add(var_ref)

    # 1) Fetch immediate child variables at this level
    seq, vars_list = fetch_variables(sock, seq, var_ref)

    result = []
    for v in vars_list:
        child_ref = v.get("variablesReference", 0)
        item = {
            "name": v["name"],
            "value": v.get("value", ""),
            "type": v.get("type", ""),
            "evaluateName": v.get("evaluateName"),
            "variablesReference": child_ref,
            "children": [],
        }

        # If this variable itself has children, recurse (within depth)
        if child_ref > 0 and depth > 0:
            seq, child_vars = fetch_variable_tree(
                sock, seq, child_ref, depth=depth - 1, visited=visited
            )
            item["children"] = child_vars

        result.append(item)

    return seq, result


def dap_client(depth_limit: int):
    """
    Example DAP client that:
      1. Connects to debugpy,
      2. Attaches to a running Python script,
      3. Sends configurationDone,
      4. Pauses the first thread,
      5. Reads the stack trace,
      6. For each frame, fetches all scopes (locals, globals, closures, etc.),
      7. Recursively expands variables up to DEPTH_LIMIT,
      8. Returns a structure with all frames and scopes.
    """

    print(f"Connecting to {HOST}:{PORT}...")
    print(f"Depth limit: {depth_limit}")
    sock = socket.create_connection((HOST, PORT))
    sock.settimeout(10.0)

    seq = 1

    # 1) "initialize"
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

    # 2) "attach"
    seq = send_dap_request(sock, seq, "attach", {"subProcess": False})
    print("Sent 'attach' request.")

    # 3) "configurationDone"
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

    # 4) "threads"
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
        return {"frames": []}

    # Pause the first thread to ensure we can see meaningful variable data
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

    # 5) "stackTrace"
    seq = send_dap_request(
        sock,
        seq,
        "stackTrace",
        {
            "threadId": thread_id,
            "startFrame": 0,
            "levels": 50,  # raise if you suspect more frames
        },
    )
    stack_trace_response = None
    while not stack_trace_response:
        msg = read_dap_message(sock)
        if msg.get("type") == "response" and msg.get("command") == "stackTrace":
            stack_trace_response = msg
        else:
            print("Got message (waiting for stackTrace):", msg)

    frames_data = []
    frames = stack_trace_response["body"].get("stackFrames", [])
    print(f"Found {len(frames)} frames in stackTrace.")

    for frame_info in frames:
        frame_id = frame_info["id"]
        fn_name = frame_info["name"]
        source_path = frame_info.get("source", {}).get("path", "no_source")
        print(f"Frame {frame_id}: {fn_name} @ {source_path}")

        # 6) "scopes" for each frame
        seq = send_dap_request(sock, seq, "scopes", {"frameId": frame_id})
        scopes_response = None
        while not scopes_response:
            msg = read_dap_message(sock)
            if msg.get("type") == "response" and msg.get("command") == "scopes":
                scopes_response = msg
            else:
                print("Got message (waiting for scopes):", msg)

        scope_list = scopes_response["body"].get("scopes", [])

        # We'll store all scopes in a dict keyed by scope name
        scope_dict = {}
        for scope_info in scope_list:
            scope_name_original = scope_info["name"]
            scope_name_lower = scope_name_original.lower()
            scope_ref = scope_info["variablesReference"]
            print(f"  Scope: {scope_name_original} (ref={scope_ref})")

            # Recursively expand variables in this scope
            seq, var_tree = fetch_variable_tree(sock, seq, scope_ref, depth=depth_limit)
            # Store them under the scope name (lowercased or original, your choice)
            scope_dict[scope_name_lower] = var_tree

        frames_data.append(
            {
                "id": frame_id,
                "functionName": fn_name,
                "sourcePath": source_path,
                "scopes": scope_dict,
            }
        )

    print("Done collecting variables. Closing socket.")
    sock.close()

    # Remove globals scope if exactly the same as locals
    for frame in frames_data:
        if "globals" in frame["scopes"]:
            if len(frame["scopes"]["globals"]) == len(frame["scopes"]["locals"]):
                print(f"Removing 'globals' scope as it's the same length as 'locals'")
                del frame["scopes"]["globals"]

    # Return everything
    return {"frames": frames_data}


if __name__ == "__main__":
    result = dap_client(depth_limit=2)
    print("\n=== Final Expanded Frames ===\n")
    print(json.dumps(result, indent=2))
