import hyperdiv as hd
from dap_client import *

VARIABLE_NAMES_TO_FILTER = [
    "__builtins__",
    "__doc__",
    "__loader__",
    "__name__",
    "__package__",
    "__spec__",
]
VARIABLE_TYPES_TO_FILTER = ["builtin_function_or_method"]  # Dont display these


def render_variable_table(variables, indent=0):
    """
    Renders a list of variables (each may have 'children') in a nested table format.
    'indent' is used to indent child rows for clarity.
    """
    # Each call to this function can create its own <tbody> or <ul> or whatever you prefer
    for v in variables:
        name = v["name"]
        value = v.get("value", "unknown")
        var_type = v.get("type", "unknown")
        evaluate_name = v.get("evaluateName", "")
        children = v.get("children", [])

        # Render one row for the variable
        with hd.scope(v):
            # Filter out certain variable names
            if name in VARIABLE_NAMES_TO_FILTER:
                # quit()
                print(f"Skipping variable: {name}")
                continue
            # Filter out certain variable types
            if var_type in VARIABLE_TYPES_TO_FILTER:
                continue
            print(f"Rendering variable: {name}")
            with hd.tr():
                # Use padding or spacing to show "indentation" visually
                # (You could also do a nested table approach.)
                with hd.td():
                    hd.markdown(f"**{name}**")
                hd.td(f"`{value}`")
                hd.td(var_type)
                hd.td(evaluate_name)
                hd.td(v.get("variablesReference", 0))

            # If this variable has child variables, recurse
            if children:
                render_variable_table(children, indent=indent + 1)


def pov():
    hd.markdown("## Python Object Viewer")
    hd.divider(spacing=1, thickness=0)

    dap_task = hd.task()
    dap_task.run(dap_client)

    if dap_task.running:
        hd.markdown("## Waiting for variables...")
        hd.spinner()

    if dap_task.error:
        print("Error collecting variables.")
        hd.markdown("`Error collecting variables`")
        return

    if dap_task.done:
        hd.markdown("### Variables")
        hd.divider(spacing=1)

        results = dap_task.result  # This is the dict returned by dap_client()
        # print(f"Results: {results}")
        globals_scope = results.get("globals", [])
        locals_scope = results.get("locals", [])

        # Sort by 'name' (optional)
        globals_scope.sort(key=lambda x: x["name"])
        locals_scope.sort(key=lambda x: x["name"])
        # print(f"Globals: {globals_scope}")

        hd.markdown("### Globals")
        with hd.table():
            # Table header
            with hd.thead():
                with hd.tr():
                    hd.td("Name")
                    hd.td("Value")
                    hd.td("Type")
                    hd.td("Evaluation Name")
                    hd.td("Ref")
            # Table body
            with hd.tbody():
                render_variable_table(globals_scope, indent=0)

        hd.divider(spacing=2)

        hd.markdown("### Locals")
        with hd.table():
            # Table header
            with hd.thead():
                with hd.tr():
                    hd.td("Name")
                    hd.td("Value")
                    hd.td("Type")
                    hd.td("Evaluation Name")
                    hd.td("Ref")
            # Table body
            with hd.tbody():
                render_variable_table(locals_scope, indent=0)


hd.run(
    pov,
    index_page=hd.index_page(
        title="Python Object Viewer",
    ),
)
