import hyperdiv as hd
from dap_client import *


# Variables to filter out from the display
## These tend to be boilerplate or internal variables that are not interesting to display
VARIABLE_NAMES_TO_FILTER = [
    "__builtins__",
    "__doc__",
    "__loader__",
    "__name__",
    "__package__",
    "__spec__",
    "special variables",
    "function variables",
    "module variables",
    "class variables",
]
VARIABLE_TYPES_TO_FILTER = [
    "builtin_function_or_method",
    "method-wrapper",
]


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


def render_tree(variables, title):
    with hd.box(border="0px solid blue", padding=0.8):
        hd.markdown(f"### {title}")
        with hd.tree(indent_guide_width="1px"):
            render_variable_tree(variables)


def render_variable_tree(variables):
    """
    Renders a list of variables (each may have 'children') in a nested tree format.
    """
    for v in variables:
        name = v["name"]
        value = v.get("value", "unknown")
        var_type = v.get("type", "unknown")
        evaluate_name = v.get("evaluateName", "")
        children = v.get("children", [])

        # Filter out certain variable names
        if name in VARIABLE_NAMES_TO_FILTER:
            continue
        # Filter out certain variable types
        if var_type in VARIABLE_TYPES_TO_FILTER:
            continue

        # Render one node for the variable
        with hd.scope(v):
            # print(f"DEBUG: Rendering variable: {name} with value: {value}")
            with hd.tree_item():
                # hd.markdown(f"**{name}**")
                # hd.markdown(f"{name}")
                # hd.markdown(f"`{value}`")
                # hd.markdown(f"`{var_type}`")
                # hd.markdown(f"`{evaluate_name}`")
                # hd.markdown(f"`{v.get('variablesReference', 0)}`")

                hd.markdown(f"**{name}**: `{value}` (**Type**: `{var_type}`) ")
                if name != evaluate_name and evaluate_name:
                    hd.markdown(" &nbsp;&nbsp;&nbsp;  ")
                    hd.markdown(f" **Evaluate Name**: `{evaluate_name}`")

                # If this variable has child variables, recurse
                if children:
                    render_variable_tree(children)


def pov():
    with hd.hbox(gap=1, justify="space-around", border="0px solid red", padding=0.8):
        with hd.box(
            font_size=1, gap=0, justify="space-around", border="0px solid yellow"
        ):
            hd.markdown("## Python Object Viewer")
            hd.divider(spacing=0.4, thickness=0)

            dap_task = hd.task()
            dap_task.run(dap_client)

            if dap_task.running:
                hd.markdown("## Waiting for variables...")
                with hd.hbox(font_size=4, justify="space-around"):
                    hd.spinner(speed="5s", track_width=0.5)

            if dap_task.error:
                hd.markdown("`Error collecting variables`")
                return

            if dap_task.done:
                # hd.markdown("### Variables")
                # hd.divider(spacing=1)

                results = dap_task.result  # This is the dict returned by dap_client()
                # print(f"Results: {results}")
                globals_scope = results.get("globals", [])
                locals_scope = results.get("locals", [])

                # Sort by 'name' (optional) -- think this messes up the order of variables / children references
                # globals_scope.sort(key=lambda x: x.get("name", "").lower())
                # locals_scope.sort(key=lambda x: x.get("name", "").lower())

                # Original table method - doesnt work well with nested variables
                # render_table(globals_scope, "Globals")
                # render_table(locals_scope, "Locals")

                # Tree method
                with hd.hbox(gap=1):
                    render_tree(locals_scope, "Locals")
                hd.divider(spacing=2)
                with hd.hbox(gap=1):
                    render_tree(globals_scope, "Globals")


hd.run(
    pov,
    index_page=hd.index_page(
        title="Python Object Viewer",
    ),
)
