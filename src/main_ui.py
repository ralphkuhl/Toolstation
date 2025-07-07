import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import os
import sys
import uuid # Nodig voor type hints als we PatchedFixture direct gebruiken

# --- Sys.path aanpassing voor directe uitvoering ---
_UI_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _UI_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _UI_SCRIPT_DIR)
# --- Einde sys.path aanpassing ---

from fixture_manager import FixtureManager, PatchedFixture # Importeer PatchedFixture ook
from dmx_controller import DMXController
from fixture_models import FixtureDefinition # Voor type hints

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DMX Light Controller")
        self.geometry("1200x750") # Iets groter voor meer ruimte

        self.fixture_manager = None
        self.dmx_controller = None
        self._fixture_definition_cache = {} # Cache voor snelle toegang tot definities via listbox index

        # Probeer FixtureManager te initialiseren
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # /app
            fixture_dir_abs = os.path.join(project_root, "fixtures")

            if not os.path.isdir(fixture_dir_abs): # Fallback als /app/fixtures niet bestaat
                alt_fixture_dir = os.path.join(_UI_SCRIPT_DIR, "..", "fixtures") # src/../fixtures
                if os.path.isdir(os.path.normpath(alt_fixture_dir)):
                    fixture_dir_abs = os.path.normpath(alt_fixture_dir)
                else:
                    # Laatste fallback: fixtures map in huidige werkdirectory
                    fixture_dir_abs = os.path.join(os.getcwd(), "fixtures")

            print(f"UI: Attempting to use fixture directory: {fixture_dir_abs}")
            self.fixture_manager = FixtureManager(fixture_directory=fixture_dir_abs)
            if not self.fixture_manager.get_available_definitions() and os.path.isdir(fixture_dir_abs) :
                 messagebox.showwarning("Fixture Warning", f"No fixture definitions loaded from {fixture_dir_abs}, although directory exists. Check JSON files.")
            elif not os.path.isdir(fixture_dir_abs):
                 messagebox.showerror("Fixture Error", f"Fixture directory not found: {fixture_dir_abs}")


        except Exception as e:
            messagebox.showerror("FixtureManager Error", f"Failed to initialize FixtureManager: {e}\nAttempted fixture directory: {fixture_dir_abs if 'fixture_dir_abs' in locals() else 'unknown'}")
            # Optioneel: self.destroy() als dit kritiek is

        # Probeer DMX Controller te initialiseren
        try:
            # auto_start_thread=False is veiliger, start het expliciet na UI setup indien nodig
            self.dmx_controller = DMXController(auto_start_thread=False)
            if not self.dmx_controller.dmx_sender:
                 messagebox.showwarning("DMX Warning", "DMX Hardware (FTDI) not found or failed to initialize. Controller will run without DMX output.")
            else:
                self.dmx_controller.start_dmx_output() # Start als sender OK is
        except Exception as e:
            messagebox.showerror("DMXController Error", f"Failed to initialize DMXController: {e}")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._create_widgets()
        if self.fixture_manager: # Alleen populeren als manager succesvol is geïnitialiseerd
            self.populate_fixture_definitions_list()
            self.update_patched_fixtures_display()

    def _create_widgets(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        self.btn_refresh_definitions = ttk.Button(top_frame, text="Refresh Definitions", command=self.refresh_fixture_definitions)
        self.btn_refresh_definitions.pack(side=tk.LEFT, padx=5)
        self.btn_blackout = ttk.Button(top_frame, text="BLACKOUT", command=self.emergency_blackout, style="Blackout.TButton")
        self.style = ttk.Style(self)
        self.style.configure("Blackout.TButton", foreground="white", background="red", font=('Helvetica', '10', 'bold'))
        self.btn_blackout.pack(side=tk.RIGHT, padx=5)


        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        patch_area_frame = ttk.LabelFrame(main_paned_window, text="Patch & Definitions", padding=10)
        main_paned_window.add(patch_area_frame, weight=1)

        controls_master_frame = ttk.LabelFrame(main_paned_window, text="Live Controls", padding=10)
        main_paned_window.add(controls_master_frame, weight=3)

        # --- Widgets in patch_area_frame ---
        definitions_outer_frame = ttk.Frame(patch_area_frame)
        definitions_outer_frame.pack(fill=tk.X, pady=5)

        search_label = ttk.Label(definitions_outer_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=(0,5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_fixture_definitions_list())
        search_entry = ttk.Entry(definitions_outer_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0,5), fill=tk.X, expand=True)

        definitions_list_frame = ttk.Frame(patch_area_frame)
        definitions_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.fixture_definitions_listbox = tk.Listbox(definitions_list_frame, height=15, exportselection=False)
        self.fixture_definitions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        defs_scrollbar = ttk.Scrollbar(definitions_list_frame, orient=tk.VERTICAL, command=self.fixture_definitions_listbox.yview)
        defs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fixture_definitions_listbox.config(yscrollcommand=defs_scrollbar.set)

        self.btn_add_to_patch = ttk.Button(patch_area_frame, text="Add Selected to Patch", command=self.add_selected_fixture_to_patch)
        self.btn_add_to_patch.pack(pady=5, fill=tk.X)

        # --- Widgets in controls_master_frame (voor gepatchte fixtures) ---
        self.patched_fixtures_canvas = tk.Canvas(controls_master_frame, highlightthickness=0)
        self.patched_fixtures_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patched_scrollbar = ttk.Scrollbar(controls_master_frame, orient=tk.VERTICAL, command=self.patched_fixtures_canvas.yview)
        patched_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.patched_fixtures_canvas.configure(yscrollcommand=patched_scrollbar.set)
        self.patched_fixtures_inner_frame = ttk.Frame(self.patched_fixtures_canvas, padding=5)
        self.canvas_window_id = self.patched_fixtures_canvas.create_window((0, 0), window=self.patched_fixtures_inner_frame, anchor="nw")
        self.patched_fixtures_inner_frame.bind("<Configure>", self._on_inner_frame_configure)
        # Bind mousewheel to the canvas that actually needs scrolling
        self.patched_fixtures_canvas.bind_all("<MouseWheel>", lambda event, canvas=self.patched_fixtures_canvas: self._on_mousewheel_specific_canvas(event, canvas))


    def _on_inner_frame_configure(self, event=None):
        self.patched_fixtures_canvas.configure(scrollregion=self.patched_fixtures_canvas.bbox("all"))
        self.patched_fixtures_canvas.itemconfigure(self.canvas_window_id, width=self.patched_fixtures_canvas.winfo_width())

    def _on_mousewheel_specific_canvas(self, event, canvas: tk.Canvas):
        # Check if the event widget is the canvas or a child of it.
        # widget_under_cursor = self.winfo_containing(event.x_root, event.y_root)
        # current_widget = widget_under_cursor
        # while current_widget is not None:
        #     if current_widget == canvas:
        #         break
        #     current_widget = current_widget.master
        # if current_widget != canvas:
        #      return # Scroll event not for this canvas or its children

        # Simpler: just scroll the passed canvas
        if event.num == 5 or event.delta < 0: # Scroll down
            canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0: # Scroll up
            canvas.yview_scroll(-1, "units")


    def populate_fixture_definitions_list(self):
        self.fixture_definitions_listbox.delete(0, tk.END)
        self._fixture_definition_cache.clear()
        if not self.fixture_manager: return

        definitions = self.fixture_manager.get_available_definitions()
        search_term = self.search_var.get().lower()

        for idx, definition in enumerate(definitions):
            display_name = f"{definition.manufacturer} - {definition.name} ({definition.total_channels}ch)"
            passes_filter = True
            if search_term:
                if not (search_term in display_name.lower() or \
                        search_term in definition.type.lower() or \
                        search_term in definition.manufacturer.lower() or \
                        search_term in definition.name.lower()):
                    passes_filter = False

            if passes_filter:
                listbox_idx = self.fixture_definitions_listbox.size()
                self.fixture_definitions_listbox.insert(tk.END, display_name)
                self._fixture_definition_cache[listbox_idx] = definition.filepath

    def filter_fixture_definitions_list(self, *args):
        self.populate_fixture_definitions_list()

    def refresh_fixture_definitions(self):
        if self.fixture_manager:
            self.fixture_manager.load_definitions() # This prints to console
            self.populate_fixture_definitions_list()
            # messagebox.showinfo("Info", f"{len(self.fixture_manager.get_available_definitions())} fixture definitions reloaded.")

    def add_selected_fixture_to_patch(self):
        selected_indices = self.fixture_definitions_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a fixture definition.")
            return
        if not self.fixture_manager: return

        try:
            definition_filepath = self._fixture_definition_cache.get(selected_indices[0])
            if not definition_filepath:
                selected_display_name = self.fixture_definitions_listbox.get(selected_indices[0])
                messagebox.showerror("Error", f"Could not retrieve definition for '{selected_display_name}'. Cache miss.")
                return

            selected_definition = self.fixture_manager.get_definition_by_identity(definition_filepath)
            if not selected_definition:
                 messagebox.showerror("Error", f"Definition for path '{definition_filepath}' not found in manager.")
                 return

            start_address_str = simpledialog.askstring("Start Address",
                                                       f"Enter DMX start address for {selected_definition.name} (1-512):",
                                                       parent=self)
            if start_address_str:
                start_address = int(start_address_str)
                if not (1 <= start_address <= 512): raise ValueError("Address out of range 1-512.")

                # Custom name dialog
                custom_name = simpledialog.askstring("Custom Name",
                                                     f"Enter a custom name for this instance of {selected_definition.name} (optional):",
                                                     parent=self)

                patched_fixture = self.fixture_manager.add_fixture_to_patch(selected_definition.filepath, start_address, custom_name=custom_name if custom_name else None)
                if patched_fixture:
                    self.update_patched_fixtures_display()
                    self.apply_patch_to_dmx()
                else: # Error message is printed by FixtureManager, but an alert here is good too
                    messagebox.showerror("Patch Error", f"Could not patch '{selected_definition.name}'.\nIt might be an address conflict or invalid configuration. Check console for details.")

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid start address or data: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during patching: {e}")


    def update_patched_fixtures_display(self):
        for widget in self.patched_fixtures_inner_frame.winfo_children():
            widget.destroy()
        if not self.fixture_manager: return

        self.style.configure("Odd.TFrame", background="#fafafa")
        self.style.configure("Even.TFrame", background="#eeeeee")
        self.style.configure("Odd.TLabel", background="#fafafa")
        self.style.configure("Even.TLabel", background="#eeeeee")


        for row_num, patched_fixture in enumerate(self.fixture_manager.get_all_patched_fixtures()):
            frame_style = "Odd" if row_num % 2 == 0 else "Even"
            current_style = f"{frame_style}.TFrame"
            label_style = f"{frame_style}.TLabel"

            fixture_outer_frame = ttk.Frame(self.patched_fixtures_inner_frame, padding=5, style=current_style)
            fixture_outer_frame.pack(fill=tk.X, expand=True, pady=(0,3), padx=1)

            top_info_frame = ttk.Frame(fixture_outer_frame, style=current_style)
            top_info_frame.pack(fill=tk.X, expand=True)

            info_text = f"{patched_fixture.name} (Def: {patched_fixture.definition.name}) @ Addr: {patched_fixture.start_address}"
            ttk.Label(top_info_frame, text=info_text, style=label_style, font=('Helvetica', '10', 'bold')).pack(side=tk.LEFT, anchor=tk.W)
            remove_btn = ttk.Button(top_info_frame, text="X", width=2, style="Toolbutton",
                                   command=lambda pf_id=patched_fixture.id: self.remove_patched_fixture(pf_id))
            remove_btn.pack(side=tk.RIGHT, anchor=tk.N, padx=(0,2), pady=(0,2))

            channels_area_frame = ttk.Frame(fixture_outer_frame, padding=(0,3,0,0), style=current_style)
            channels_area_frame.pack(fill=tk.X, expand=True)

            items_per_row = 3
            ch_row, ch_col = 0, 0

            target_channels_data = patched_fixture.definition.channels
            if not target_channels_data:
                target_channels_data = [{'name': f"CH {i+1}", 'dmx_channel_offset': i} for i in range(patched_fixture.definition.total_channels)]

            for ch_data in target_channels_data:
                ch_f = ttk.Frame(channels_area_frame, style=current_style)
                ch_f.grid(row=ch_row, column=ch_col, padx=2, pady=2, sticky="ew")
                channels_area_frame.columnconfigure(ch_col, weight=1)

                ch_name = ch_data.name if hasattr(ch_data, 'name') else ch_data['name']
                ch_offset = ch_data.dmx_channel_offset # This must exist

                ttk.Label(ch_f, text=f"{ch_name}:", width=12, anchor="w", style=label_style).pack(side=tk.LEFT)

                current_val = patched_fixture.get_channel_value_by_offset(ch_offset)
                # scale_var moet een instance member zijn of op een andere manier bewaard blijven als je de waarde later wilt ophalen
                # Voor nu, de slider update direct de PatchedFixture.
                scale_var = tk.IntVar(value=current_val)

                cmd = lambda val, pf_id=patched_fixture.id, offset=ch_offset, var=scale_var: \
                    self.on_fixture_channel_change(pf_id, offset, int(float(val)), var)

                scale = ttk.Scale(ch_f, from_=0, to=255, orient=tk.HORIZONTAL, variable=scale_var, command=cmd)
                scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

                # Entry om waarde direct in te voeren
                entry_var = tk.StringVar(value=str(current_val))

                def entry_cmd_factory(pf_id, offset, var_entry, var_scale):
                    def callback(event=None): # event is voor <Return> binding
                        try:
                            new_val_entry = int(var_entry.get())
                            if 0 <= new_val_entry <= 255:
                                self.on_fixture_channel_change(pf_id, offset, new_val_entry, var_scale)
                                var_scale.set(new_val_entry) # Update de slider ook
                            else:
                                var_entry.set(str(var_scale.get())) # Reset naar slider waarde
                        except ValueError:
                            var_entry.set(str(var_scale.get())) # Reset naar slider waarde bij foute input
                    return callback

                entry_callback = entry_cmd_factory(patched_fixture.id, ch_offset, entry_var, scale_var)
                entry = ttk.Entry(ch_f, textvariable=entry_var, width=4, justify='right')
                entry.bind("<Return>", entry_callback)
                entry.bind("<FocusOut>", entry_callback) # Update ook bij focus out
                entry.pack(side=tk.LEFT, padx=2)


                # Initial sync slider var met entry var (omdat slider de scale_var update)
                scale_var.trace_add("write", lambda *args, ev=entry_var, sv=scale_var: ev.set(str(sv.get())))


                ch_col += 1
                if ch_col >= items_per_row:
                    ch_col = 0
                    ch_row += 1

        self.patched_fixtures_inner_frame.update_idletasks()
        self._on_inner_frame_configure()

    def on_fixture_channel_change(self, patched_fixture_id: uuid.UUID, channel_offset: int, new_value: int, scale_variable_ref: tk.IntVar):
        # scale_variable_ref is de tk.IntVar van de slider. Deze wordt al geupdate door de slider zelf.
        # We moeten alleen de PatchedFixture updaten en DMX sturen.
        if not self.fixture_manager: return
        patched_fixture = self.fixture_manager.get_patched_fixture_by_id(patched_fixture_id)
        if patched_fixture:
            patched_fixture.set_channel_value_by_offset(channel_offset, new_value)
            self.apply_patch_to_dmx()
            # De gekoppelde Entry wordt geupdate via de trace op scale_variable_ref

    def remove_patched_fixture(self, patched_fixture_id: uuid.UUID):
        if not self.fixture_manager: return
        pf = self.fixture_manager.get_patched_fixture_by_id(patched_fixture_id)
        if pf and messagebox.askyesno("Confirm Remove", f"Remove '{pf.name}' from patch?"):
            if self.fixture_manager.remove_fixture_from_patch(patched_fixture_id):
                self.update_patched_fixtures_display()
                self.apply_patch_to_dmx()

    def apply_patch_to_dmx(self):
        if self.fixture_manager and self.dmx_controller:
            self.fixture_manager.apply_patch_to_dmx_controller(self.dmx_controller)

    def emergency_blackout(self):
        if self.dmx_controller:
            self.dmx_controller.blackout()
            if self.fixture_manager:
                for pf in self.fixture_manager.get_all_patched_fixtures():
                    for i in range(pf.definition.total_channels):
                        pf.set_channel_value_by_offset(i, 0)
                self.update_patched_fixtures_display()
            messagebox.showinfo("Blackout", "All DMX channels set to 0.")


    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.dmx_controller:
                print("UI: Closing DMX Controller...")
                self.dmx_controller.close()
            self.destroy()

if __name__ == '__main__':
    MOCK_DMX_FOR_UI_DEV = True

    if MOCK_DMX_FOR_UI_DEV:
        class DummyDMXController:
            def __init__(self, device_id=None, auto_start_thread=True): self.dmx_sender = True; print("MockDMX: Initialized")
            def set_channels(self, start, vals): pass
            def get_all_values(self): return bytearray(512)
            def start_dmx_output(self): print("MockDMX: Output started")
            def blackout(self): print("MockDMX: Blackout called")
            def close(self): print("MockDMX: Closed.")

        import dmx_controller as real_dmx_module
        real_dmx_module.DMXController = DummyDMXController # Monkey patch
        print("INFO: Using MOCKED DMXController for UI testing.")

    app = App()
    app.mainloop()
