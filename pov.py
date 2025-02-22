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
    "debugpy",
]
VARIABLE_TYPES_TO_FILTER = [
    "builtin_function_or_method",
    "method-wrapper",
]


def render_tree(variables, title):
    with hd.box(border="0px solid blue", padding=0.8):
        with hd.tree(indent_guide_width="1px"):
            render_variable_tree(variables)


def render_variable_tree(variables):
    """
    Renders a list of variables (each may have 'children') in a nested tree format.
    """
    for v in variables:
        # print(f"Rendering variable tree for: {v}")
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
            font_size=1,
            gap=0,
            justify="space-around",
            border="0px solid yellow",
            align="center",
        ):
            hd.markdown("## Python Object Viewer")
            hd.divider(spacing=0.4, thickness=0)

            dap_task = hd.task()
            dap_task.run(dap_client)

            if dap_task.running:
                hd.markdown("### Waiting for variables...")
                hd.markdown("&nbsp;")  # hack to add some space
                with hd.hbox(font_size=4, justify="space-around"):
                    hd.spinner(speed="5s", track_width=0.5)
                hd.markdown("&nbsp;")  # hack to add some space
                hd.markdown(
                    "This can take a couple of minutes, depending on the size of your program."
                )

            if dap_task.error:
                hd.markdown("`Error collecting variables`")
                return

            if dap_task.done:
                print("dap_task is done")
                results = dap_task.result  # This is the dict returned by dap_client()

                # If no frames, nothing to display
                frames = results.get("frames", [])
                if not frames:
                    print("No frames returned from dap_client. Re-running.")
                    dap_task.clear()
                    dap_task.run(dap_client)
                    return

                # Right now we only get one frame, so we'll just use that
                first_frame = frames[0]
                dap_scopes = first_frame.get("scopes", {})
                print(f"Scopes available: {list(dap_scopes.keys())}")

                # Count variables in each scope
                for scope_list in dap_scopes.keys():
                    print(
                        f"Scope: {scope_list} has {len(dap_scopes[scope_list])} variables"
                    )

                # Create a tab group for all scope names
                tabs_dict = {}
                with hd.tab_group():
                    for scope_name in dap_scopes.keys():
                        with hd.scope(scope_name):
                            # Create a tab with the title = scope_name.title()
                            tab_obj = hd.tab(scope_name.title())
                            # Store the tab object in a dict so we can check if it's active later
                            tabs_dict[scope_name] = tab_obj

                # Now show the variables for whichever tab is active
                with hd.hbox(gap=1):
                    # We'll iterate again to find the active tab
                    for scope_name, tab_obj in tabs_dict.items():
                        with hd.scope(tab_obj):
                            if tab_obj.active:
                                scope_vars = dap_scopes[scope_name]
                                render_tree(
                                    scope_vars, title=f"{scope_name.title()} Scope"
                                )


hd.run(
    pov,
    index_page=hd.index_page(
        title="Python Object Viewer",
    ),
)
