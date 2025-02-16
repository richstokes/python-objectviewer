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
VARIABLE_TYPES_TO_FILTER = [
    "builtin_function_or_method",
    "method-wrapper",
]  # Dont display these


def render_table(variables, title):
    hd.markdown(f"### {title}")
    with hd.table():
        # Table header
        with hd.thead():
            with hd.tr():
                hd.td("Name")
                hd.td("Ident")  # Testing
                hd.td("Value")
                hd.td("Type")
                hd.td("Evaluation Name")
                hd.td("Ref")
        # Table body
        with hd.tbody():
            render_variable_table(variables, indent=0)
    hd.divider(spacing=2)


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
                continue
            # Filter out certain variable types
            if var_type in VARIABLE_TYPES_TO_FILTER:
                continue
            print(f"Rendering variable: {name} with value: {value}")
            with hd.tr():
                # TODO: Display values differently based on type
                # TODO: Use padding or spacing to show "indentation" visually
                with hd.td():
                    hd.markdown(f"**{name}**")
                hd.td(f"{indent}")
                with hd.td():
                    if value:
                        hd.markdown(f"`{value}`")
                    else:
                        hd.markdown("`None`")
                with hd.td():
                    if var_type:
                        hd.markdown(f"`{var_type}`")
                    else:
                        hd.markdown("`None`")
                with hd.td():
                    hd.markdown(f"`{evaluate_name}`")
                with hd.td():
                    hd.markdown(f"`{v.get('variablesReference', 0)}`")

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
        with hd.box(font_size=4):
            hd.spinner(speed="5s", track_width=0.5)

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

        # Sort by 'name' (optional) -- think this messes up the order of variables / children references
        # globals_scope.sort(key=lambda x: x.get("name", "").lower())
        # locals_scope.sort(key=lambda x: x.get("name", "").lower())
        # print(f"Globals: {globals_scope}")

        render_table(globals_scope, "Globals")
        render_table(locals_scope, "Locals")


hd.run(
    pov,
    index_page=hd.index_page(
        title="Python Object Viewer",
    ),
)
