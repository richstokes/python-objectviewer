import hyperdiv as hd
from dap_client import *


def pov():
    hd.markdown("## Python Object Viewer")
    # hd.divider(spacing=1)

    dap_task = hd.task()
    dap_task.run(dap_client)

    if dap_task.running:
        hd.markdown("## Waiting for variables...")

    if dap_task.error:
        print("Error collecting variables.")
        hd.markdown("`Error collecting variables`")
        return

    if dap_task.done:
        hd.markdown("### Variables")
        hd.divider(spacing=1)
        # print(f"DEBUG dap_task.result: \n\n{dap_task.result}")

        # Sort variables by name
        globals_scope = dap_task.result.get("globals", [])
        locals_scope = dap_task.result.get("locals", [])

        # print(f"DEBUG globals_scope: \n\n{globals_scope}")
        # print(f"DEBUG locals_scope: \n\n{locals_scope}")

        # sort by name
        globals_scope = sorted(globals_scope, key=lambda x: x["name"])
        locals_scope = sorted(locals_scope, key=lambda x: x["name"])

        hd.markdown("### Globals")
        with hd.table():
            # Table header
            with hd.thead():
                # Header row
                with hd.tr():
                    hd.td("Name")
                    hd.td("Value")
                    hd.td("Type")
                    hd.td("Evaluation Name")
                    hd.td("Reference")

            for v in globals_scope:
                with hd.scope(v):
                    name = v["name"]
                    value = v.get("value", "unknown")
                    var_type = v.get("type", "unknown")
                    var_evaulation_name = v.get("evaluateName", "unknown")
                    var_ref = v.get("variablesReference", "unknown")

                    if name == "special variables":  # Filter as these are not useful?
                        continue

                    # Table body
                    with hd.tbody():
                        # Body rows
                        with hd.tr():
                            hd.td(name)
                            with hd.td():
                                hd.markdown(f"`{value}`")
                            hd.td(var_type)
                            hd.td(var_evaulation_name)
                            hd.td(var_ref)

        hd.divider(spacing=2)
        hd.markdown("### Locals")
        with hd.table():
            # Table header
            with hd.thead():
                # Header row
                with hd.tr():
                    hd.td("Name")
                    hd.td("Value")
                    hd.td("Type")
                    hd.td("Evaluation Name")
                    hd.td("Reference")

            for v in locals_scope:
                with hd.scope(v):
                    name = v["name"]
                    value = v.get("value", "unknown")
                    var_type = v.get("type", "unknown")
                    var_evaulation_name = v.get("evaluateName", "unknown")
                    var_ref = v.get("variablesReference", "unknown")

                    if name == "special variables":  # Filter as these are not useful?
                        continue

                    # Table body
                    with hd.tbody():
                        # Body rows
                        with hd.tr():
                            hd.td(name)
                            with hd.td():
                                hd.markdown(f"`{value}`")
                            hd.td(var_type)
                            hd.td(var_evaulation_name)
                            hd.td(var_ref)


hd.run(
    pov,
    index_page=hd.index_page(
        title="Python Object Viewer",
    ),
)
