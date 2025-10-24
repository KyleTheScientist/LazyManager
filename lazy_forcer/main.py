import sys
import json
import dearpygui.dearpygui as dpg

from pathlib import Path
from tinydb import Query, TinyDB
from tinydb.storages import MemoryStorage

from connection import Mailman, Outcome


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent
    
    return base_path / relative_path

# Load all bingo entries into in-memory database
files = resource_path("bingo/").glob("**/*.json")
db = TinyDB(storage=MemoryStorage)
for file in files:
    properties = json.load(file.open("r"))
    db.insert(properties)


def pattern_changed(sender, app_data, user_data):
    for table_row in dpg.get_item_children("entry_table", 1):
        for selectable in dpg.get_item_children(table_row, 1):
            dpg.set_value(selectable, False)


def selected_entry_callback(sender, app_data, user_data):
    entry, row = user_data
    for table_row in dpg.get_item_children("entry_table", 1):
        for selectable in dpg.get_item_children(table_row, 1):
            dpg.set_value(selectable, dpg.get_item_alias(table_row) == f"row_{row}")

    pattern = entry.get("pattern", [])
    for i in range(25):
        bit = (pattern >> i) & 1
        x = i % 5
        y = i // 5
        dpg.set_value(f"pattern_{y}_{x}", bool(bit))

    dpg.set_value("match_in", entry.get("matchIn", 0))


def sort_table(sender, sort_specs):
    col, direction = sort_specs[0]
    print(dpg.get_item_alias(col), direction)

    rows = dpg.get_item_children("entry_table", 1)

    def sort_key(row):
        entry = dpg.get_item_user_data(row)
        value = entry.get(dpg.get_item_alias(col).split("_", 1)[1], "")
        value = str(value)
        return len(value) * 10 + (int(value) if value.isdecimal() else 0)

    rows.sort(key=sort_key, reverse=(direction < 0))
    dpg.reorder_items(sender, 1, rows)


def build_entry_table(bingo_tables):
    dpg.delete_item("entry_window", children_only=True)

    dpg.push_container_stack("entry_window")
    row = 0
    last_column = None
    with dpg.table(
        tag="entry_table",
        header_row=True,
        resizable=False,
        policy=dpg.mvTable_SizingFixedFit,
        width=-1,
        height=-1,
        scrollX=True,
        scrollY=True,
        sortable=True,
        callback=sort_table,
    ):
        for table in bingo_tables:
            entries = table.get("entries", [])
            columns = set(key for entry in entries for key in entry.keys())
            columns = sorted(columns)
            # move patterns and matchIN to the front
            if "matchIn" in columns:
                columns.remove("matchIn")
                columns.insert(0, "matchIn")
            if "pattern" in columns:
                columns.remove("pattern")
                columns.insert(0, "pattern")

            for col in columns:
                tag = f"col_{col}"
                if not dpg.does_item_exist(tag):
                    last_column = dpg.add_table_column(
                        label=col, tag=tag, prefer_sort_descending=True, prefer_sort_ascending=False
                    )

            for entry in entries:
                with dpg.table_row(tag=f"row_{row}", user_data=entry):
                    for col in columns:
                        value = entry.get(col, "")
                        dpg.add_selectable(
                            label=str(value),
                            callback=selected_entry_callback,
                            user_data=(entry, row),
                            span_columns=True,
                        )
                row += 1
            if row > 1000:
                break
    dpg.pop_container_stack()
    print("done")


def reset_downstream(sender):
    return
    combos = ["paytable_combo", "percentage_combo", "table_name_combo", "denom_combo", "bet_level_combo"]
    index = combos.index(sender)
    print(f"Resetting downstream combos after {sender}")
    for tag in combos[index + 1 :]:
        print(f" - Resetting {tag}")
        dpg.configure_item(tag, items=[])
        dpg.set_value(tag, "")


def filter_changed(sender, app_data, user_data):
    print(sender)
    reset_downstream(sender)

    condition = Query()

    # Filter by paytable
    paytable = dpg.get_value("paytable_combo")
    condition = condition.configuration.name == paytable
    table_name = dpg.get_value("table_name_combo")
    percentages = sorted(set(str(item["configuration"]["percentage"]) for item in db.search(condition)))
    dpg.configure_item("percentage_combo", items=percentages)

    # Filter by percentage
    percentage = dpg.get_value("percentage_combo")
    if percentage:
        condition = condition & (Query().configuration.percentage == int(percentage))
        table_names = sorted(set(item["configuration"]["tableName"] for item in db.search(condition)))
        dpg.configure_item("table_name_combo", items=table_names)

    # Filter by table name
    table_name = dpg.get_value("table_name_combo")
    if table_name:
        condition = condition & (Query().configuration.tableName == table_name)

    docs = db.search(condition)

    # Filter by denomination
    denoms = set()
    for doc in docs:
        denoms.update(doc["configuration"]["betLevelGroups"])
    denoms = sorted(list(int(denom) for denom in denoms))
    dpg.configure_item("denom_combo", items=list(denoms))

    # Filter by bet level
    denom = dpg.get_value("denom_combo")
    if denom:
        bet_levels = set()
        for doc in docs:
            if denom in doc["configuration"]["betLevelGroups"]:
                bet_levels.update(doc["configuration"]["betLevelGroups"][denom])
        bet_levels = sorted(list(int(level) for level in bet_levels))
        dpg.configure_item("bet_level_combo", items=list(bet_levels))

    filtered_docs = []
    for doc in docs:
        if denom:
            if denom not in doc["configuration"]["betLevelGroups"]:
                continue
            bet_levels = doc["configuration"]["betLevelGroups"][denom]
            level = dpg.get_value("bet_level_combo")
            if level and int(level) not in bet_levels:
                continue
        filtered_docs.append(doc)

    print(f"Filtered down to {len(filtered_docs)} entries")
    build_entry_table(filtered_docs)


def queue_pattern():
    pattern = 0
    for y in range(5):
        for x in range(5):
            if dpg.get_value(f"pattern_{y}_{x}"):
                pattern |= 1 << (y * 5 + x)

    dpg.push_container_stack("queue_table")
    with dpg.table_row():
        dpg.add_button(label="X", width=20, callback=lambda s, a, u: dpg.delete_item(dpg.get_item_parent(s)))
        dpg.add_text(dpg.get_value("match_in"))
        dpg.add_text(pattern)

def popup(text):
    if dpg.does_item_exist("result_window"):
        dpg.delete_item("result_window")
    
    with dpg.window(tag="result_window", label="Result", width=400, height=100, modal=True) as popup:
        vw, vh = dpg.get_viewport_width(), dpg.get_viewport_height()
        w, h = vw * 0.5, 100
        dpg.set_item_width(popup, w)
        dpg.set_item_pos(popup, [(vw - w) // 2, (vh - h) // 2])
        
        dpg.add_text(text)
        dpg.add_spacer(height=5)
        dpg.add_button(label="Close", width=-1, callback=lambda: dpg.delete_item("result_window"))

def force_queued_patterns():
    if not dpg.get_item_children("queue_table", 1):
        popup("No patterns queued")
        return

    mailman = Mailman("10.1.1.254", 25557)
    site_id = ""
    client_ip = ""
    outcomes = []
    for row in dpg.get_item_children("queue_table", 1):
        children = dpg.get_item_children(row, 1)
        match_in = int(dpg.get_value(children[1]))
        pattern = int(dpg.get_value(children[2]))
        outcome = Outcome(pattern=pattern, match_in=match_in)
        outcomes.append(outcome)

    print(f"Forcing {len(outcomes)} outcomes")
    dpg.configure_item("force_outcomes_button", enabled=False)
    dpg.configure_item("force_outcomes_button", label="...")
    success = mailman.force_outcomes(outcomes, site_id, client_ip)

    dpg.configure_item("force_outcomes_button", enabled=True)
    dpg.configure_item("force_outcomes_button", label="Force outcomes")    

    if success:
        popup("Successfully forced all outcomes")
    else:
        popup("Failed to force outcomes.\nSee console for details.")

def main():
    dpg.create_context()
    dpg.create_viewport(title="Outcome Forcer", width=730, height=800)

    paytables = []

    with dpg.window(label="Outcome Forcer", width=-1, height=-1, tag="root") as root:
        with dpg.group(width=-1):
            # Filters
            with dpg.child_window(label="Filters", width=-1, height=130, horizontal_scrollbar=True):
                paytables = sorted(set(item["configuration"]["name"] for item in db.all()))
                dpg.add_combo(
                    label="Paytable", items=paytables, width=300, tag="paytable_combo", callback=filter_changed
                )
                dpg.add_combo(label="Percentage", items=[], width=300, tag="percentage_combo", callback=filter_changed)
                dpg.add_combo(label="Table Name", items=[], width=300, tag="table_name_combo", callback=filter_changed)
                dpg.add_combo(label="Denomination", items=[], width=300, tag="denom_combo", callback=filter_changed)
                dpg.add_combo(label="Bet Level", items=[], width=300, tag="bet_level_combo", callback=filter_changed)

            # Pattern table container
            with dpg.child_window(label="Entries", tag="entry_window", width=-1, height=385, horizontal_scrollbar=True):
                dpg.add_table(tag="entry_table")

        with dpg.group():
            with dpg.group(horizontal=True):
                with dpg.child_window(label="Pattern Display", width=143, height=219):
                    dpg.add_input_int(label="Match in", tag="match_in", step=0, width=65)
                    dpg.add_spacer(height=5)
                    for y in range(5):
                        with dpg.group(horizontal=True):
                            for x in range(5):
                                dpg.add_checkbox(tag=f"pattern_{y}_{x}", label="", callback=pattern_changed)
                        if y < 4:
                            dpg.add_spacer(height=1)
                    dpg.add_spacer(height=5)
                    dpg.add_button(label="Queue pattern", width=-1, callback=queue_pattern)

                with dpg.group():
                    with dpg.child_window(label="Queue", width=-1, height=180, horizontal_scrollbar=True):
                        with dpg.table(
                            tag="queue_table",
                            resizable=False,
                            policy=dpg.mvTable_SizingFixedFit,
                            width=-1,
                            height=-1,
                            scrollX=True,
                            scrollY=True,
                        ):
                            dpg.add_table_column(label="")
                            dpg.add_table_column(label="Match In")
                            dpg.add_table_column(label="Pattern")
                    with dpg.child_window(label="Send", width=-1, height=35):
                        dpg.add_button(label="Force outcomes", tag="force_outcomes_button", width=-1, callback=lambda: force_queued_patterns())

    dpg.set_primary_window(root, True)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()


# pyinstaller --noconfirm --onefile --console --add-data "bingo/*;bingo" --name LazyForcer main.py