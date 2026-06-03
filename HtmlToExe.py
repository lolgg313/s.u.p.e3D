import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import re

class JSHECompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSHE FPS Engine - True Standalone Compiler")
        self.root.geometry("550x380")
        self.root.resizable(False, False)
        
        # Paths
        self.html_path = tk.StringVar()
        self.css_path = tk.StringVar()
        self.json_path = tk.StringVar()
        
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        header = tk.Label(self.root, text="True Standalone Game Builder", font=("Helvetica", 16, "bold"))
        header.pack(pady=15)
        
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="1. Base Engine HTML (JSHE V0.1.5.html):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.html_path, width=45).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.html_path, [("HTML Files", "*.html")])).grid(row=1, column=1)
        
        ttk.Label(frame, text="2. Engine CSS (style.css):").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.css_path, width=45).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.css_path, [("CSS Files", "*.css")])).grid(row=3, column=1)
        
        ttk.Label(frame, text="3. Saved Game Data (.json):").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.json_path, width=45).grid(row=5, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.json_path, [("JSON Map", "*.json")])).grid(row=5, column=1)
        
        compile_btn = ttk.Button(self.root, text="COMPILE STANDALONE GAME", command=self.compile_game)
        compile_btn.pack(pady=20, ipadx=10, ipady=5)

    def browse_file(self, var, filetypes):
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)

    def compile_game(self):
        html_file = self.html_path.get()
        css_file = self.css_path.get()
        json_file = self.json_path.get()

        if not all([html_file, css_file, json_file]):
            messagebox.showerror("Error", "Please select all three files before compiling.")
            return

        try:
            # 1. Read Files
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            with open(css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
            with open(json_file, 'r', encoding='utf-8') as f:
                json_content = f.read()

            # Validate JSON
            json.loads(json_content)

            # 2. Inject CSS directly into head to prevent styling flashes
            css_injection = f"<style>\n/* INJECTED BY COMPILER */\n{css_content}\n</style>"
            html_content = re.sub(r'<link[^>]*href="style\.css"[^>]*>', css_injection, html_content)

            # 3. ANNIHILATE THE EDITOR HTML 
            # We slice the string from the start of the editor all the way down to where Three.js is loaded
            start_cut = html_content.find('<div id="editor">')
            end_cut = html_content.find('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/')
            
            if start_cut != -1 and end_cut != -1:
                html_content = html_content[:start_cut] + html_content[end_cut:]
            
            # Remove the edit mode text indicator completely
            html_content = html_content.replace('<div id="mode-indicator">EDIT MODE</div>', '')

            # 4. INJECT DOM POLYFILL
            # This catches the JS trying to attach events to the editor we just deleted and provides safe dummy variables so it doesn't crash.
            polyfill = """
            <script>
            // --- STANDALONE DOM POLYFILL ---
            const originalGetElementById = document.getElementById.bind(document);
            document.getElementById = function(id) {
                let el = originalGetElementById(id);
                if (!el) {
                    el = document.createElement('div');
                    el.id = id;
                    el.value = ''; 
                }
                return el;
            };

            const originalQuerySelectorAll = document.querySelectorAll.bind(document);
            document.querySelectorAll = function(selector) {
                let nodes = originalQuerySelectorAll(selector);
                return nodes.length > 0 ? nodes : [];
            };
            </script>
            """
            html_content = html_content.replace('</head>', polyfill + '\n</head>')

            # 5. INJECT SYNCHRONOUS BOOTLOADER
            # This executes the moment the engine scripts finish defining their functions, before the first frame is drawn.
            injection_script = f"""
            <script>
            // --- INJECTED STANDALONE BOOTLOADER ---
            const standaloneMapData = {json_content};

            // Execute synchronously to bypass visual flashes
            try {{
                const data = standaloneMapData;
                
                wallTextures = data.wallTextures || INITIAL_WALL_TEXTURES;
                floorTextures = data.floorTextures || INITIAL_FLOOR_TEXTURES;

                initAudio(); 
                floorTextures.forEach((tex, index) => {{
                    if(tex.soundData) decodeTextureSound(index);
                }});
                
                STATE.selectedWallTexture = 0; 
                STATE.selectedFloorTexture = 0;
                initTextureSelectors(); 

                if (data.customEnemyModel) STATE.customEnemyModel = data.customEnemyModel;
                if (data.enemyAppearance) STATE.enemyAppearance = data.enemyAppearance;

                if (data.playerSpawn) mapData.playerSpawn = data.playerSpawn;
                updateSpawnVisual(); 

                if (data.customShootSoundData) {{
                    STATE.customShootSoundData = data.customShootSoundData;
                    loadSoundFromBase64(data.customShootSoundData);
                }}

                mapData = {{ walls: new Map(), floors: new Map(), triggers: [] }};
                triggersGroup.clear();
                importedModelsGroup.clear();
                importedModelsData = [];
                modelSources = {{}};
                updateModelListUI();

                if (data.walls) data.walls.forEach(w => mapData.walls.set(getKey(w.x, w.y, w.z), w));
                if (data.floors) data.floors.forEach(f => mapData.floors.set(getKey(f.x, 0, f.z), f));
                if (data.triggers) mapData.triggers = data.triggers;

                updateSceneVisuals();

                if (data.enemies && data.enemies.length > 0) {{
                    data.enemies.forEach(e => {{
                        let modelToUse = e.customModelData || data.customEnemyModel || null;
                        const visualType = modelToUse ? 'custom' : 'default';
                        const newEnemy = {{
                            id: e.id || (Date.now() + Math.random()),
                            type: 'enemy',
                            name: "Migrated Enemy",
                            position: {{ x: e.x, y: 0, z: e.z }},
                            rotation: {{ x: 0, y: 0, z: 0 }},
                            scale: {{ x: 1, y: 1, z: 1 }},
                            visualType: visualType,
                            customModelData: modelToUse,
                            maxHealth: e.maxHealth || 5,
                            speed: e.speed || 2,
                            damage: e.damage || 10
                        }};
                        importedModelsData.push(newEnemy);
                    }});
                }}

                if (data.modelSources) modelSources = data.modelSources;
                if (data.models) importedModelsData = [...importedModelsData, ...data.models];

                importedModelsData.forEach(modelData => {{
                    if (!modelData.sourceId && modelData.url) {{
                        const tempSourceId = 'legacy_' + modelData.id;
                        modelSources[tempSourceId] = {{ name: modelData.name, url: modelData.url }};
                        modelData.sourceId = tempSourceId;
                        delete modelData.url; 
                    }}
                    spawnModelVisuals(modelData); 
                }});

                // --- INSTANT PLAY MODE LOCK ---
                STATE.mode = 'edit'; // Set to edit so toggle flips it forward instantly
                toggleMode();
                
                // Nuke the 'E' key entirely at the highest event capture level
                window.addEventListener('keydown', (e) => {{
                    if (e.code === 'KeyE') {{
                        e.preventDefault();
                        e.stopImmediatePropagation();
                    }}
                }}, true); 

            }} catch (error) {{
                console.error('Bootloader Error:', error);
            }}
            </script>
            </body>
            """

            html_content = html_content.replace('</body>', injection_script)

            # 6. Save output
            save_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML File", "*.html")],
                title="Save Standalone Game As..."
            )
            
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                messagebox.showinfo("Success", f"True standalone game compiled successfully!\nSaved to: {save_path}")

        except Exception as e:
            messagebox.showerror("Compilation Error", f"An error occurred:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = JSHECompilerApp(root)
    root.mainloop()
