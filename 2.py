import os
import shutil
import subprocess
import zipfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- Directory Configuration ---
BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
SDK_DIR = TOOLS_DIR / "android_sdk"
JDK_DIR = TOOLS_DIR / "jdk"
GRADLE_DIR = TOOLS_DIR / "gradle"
DOWNLOADS_DIR = TOOLS_DIR / "downloads"
GRADLE_CACHE_DIR = TOOLS_DIR / "gradle_cache"  # NEW: Forced local portable cache
WORKSPACE_DIR = BASE_DIR / "workspace"
PROJECTS_DIR = WORKSPACE_DIR / "projects"
OUTPUT_DIR = WORKSPACE_DIR / "output"
KEYSTORE_DIR = WORKSPACE_DIR / "keystores"

# Ensure directories exist
for d in [TOOLS_DIR, SDK_DIR, JDK_DIR, GRADLE_DIR, DOWNLOADS_DIR, GRADLE_CACHE_DIR, WORKSPACE_DIR, PROJECTS_DIR, OUTPUT_DIR, KEYSTORE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Utility Functions ---
def log_to_widget(widget, text):
    widget.config(state="normal")
    widget.insert(tk.END, text + "\n")
    widget.see(tk.END)
    widget.config(state="disabled")
    widget.update_idletasks()

def extract_zip(zip_path, dest_dir, log_widget):
    log_to_widget(log_widget, f"Extracting: {zip_path.name}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)

def find_local_zip(pattern):
    matches = list(DOWNLOADS_DIR.glob(pattern))
    return matches[0] if matches else None

def get_single_subdir(directory):
    subdirs = [d for d in directory.iterdir() if d.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]
    return directory

# --- Engine Setup Logic (Offline-First) ---
def setup_jdk(log_widget):
    if list(JDK_DIR.glob("**/bin/java.exe")):
        log_to_widget(log_widget, "[OK] JDK is already configured.")
        return True

    zip_path = find_local_zip("*jdk*.zip")
    if not zip_path:
        log_to_widget(log_widget, "[ERROR] Missing JDK zip in downloads folder.")
        return False

    temp_dir = TOOLS_DIR / "temp_jdk"
    extract_zip(zip_path, temp_dir, log_widget)
    
    root_folder = get_single_subdir(temp_dir)
    shutil.copytree(root_folder, JDK_DIR, dirs_exist_ok=True)
    shutil.rmtree(temp_dir)
    log_to_widget(log_widget, "[SUCCESS] JDK setup complete.")
    return True

def setup_gradle(log_widget):
    if list(GRADLE_DIR.glob("**/bin/gradle.bat")):
        log_to_widget(log_widget, "[OK] Gradle is already configured.")
        return True

    zip_path = find_local_zip("gradle-*.zip")
    if not zip_path:
        log_to_widget(log_widget, "[ERROR] Missing Gradle zip in downloads folder.")
        return False

    extract_zip(zip_path, GRADLE_DIR, log_widget)
    log_to_widget(log_widget, "[SUCCESS] Gradle setup complete.")
    return True

def setup_android_sdk(log_widget):
    success = True

    platform_target = SDK_DIR / "platforms" / "android-35"
    if not platform_target.exists():
        zip_path = find_local_zip("platform-35*.zip")
        if zip_path:
            temp_dir = TOOLS_DIR / "temp_plat"
            extract_zip(zip_path, temp_dir, log_widget)
            root_folder = get_single_subdir(temp_dir)
            shutil.copytree(root_folder, platform_target, dirs_exist_ok=True)
            shutil.rmtree(temp_dir)
            log_to_widget(log_widget, "[SUCCESS] SDK Platform 35 configured.")
        else:
            log_to_widget(log_widget, "[ERROR] Missing platform-35 zip.")
            success = False
    else:
         log_to_widget(log_widget, "[OK] SDK Platform 35 already configured.")

    build_tools_target = SDK_DIR / "build-tools" / "35.0.0"
    if not build_tools_target.exists():
        zip_path = find_local_zip("build-tools*.zip")
        if zip_path:
            temp_dir = TOOLS_DIR / "temp_bt"
            extract_zip(zip_path, temp_dir, log_widget)
            root_folder = get_single_subdir(temp_dir)
            shutil.copytree(root_folder, build_tools_target, dirs_exist_ok=True)
            shutil.rmtree(temp_dir)
            log_to_widget(log_widget, "[SUCCESS] Build-Tools 35.0.0 configured.")
        else:
            log_to_widget(log_widget, "[ERROR] Missing build-tools zip.")
            success = False
    else:
         log_to_widget(log_widget, "[OK] Build-Tools 35.0.0 already configured.")

    cmd_tools_target = SDK_DIR / "cmdline-tools" / "latest"
    if not cmd_tools_target.exists():
        zip_path = find_local_zip("commandlinetools*.zip")
        if zip_path:
            temp_dir = TOOLS_DIR / "temp_cmd"
            extract_zip(zip_path, temp_dir, log_widget)
            root_folder = get_single_subdir(temp_dir)
            shutil.copytree(root_folder, cmd_tools_target, dirs_exist_ok=True)
            shutil.rmtree(temp_dir)
            log_to_widget(log_widget, "[SUCCESS] Command-line tools configured.")
        else:
            log_to_widget(log_widget, "[ERROR] Missing commandlinetools zip.")
            success = False
    else:
         log_to_widget(log_widget, "[OK] Command-line tools already configured.")

    licenses_dir = SDK_DIR / "licenses"
    licenses_dir.mkdir(exist_ok=True)
    (licenses_dir / "android-sdk-license").write_text(
        "24333f8a63b6825ea9c5514f83c2829b004d1fee\n"
        "84831b9409646a918e30573bab4c9c91346d8abd\n"
        "d975f751698a77b662f1254ddbeed3901e976f5a\n",
        encoding="utf-8"
    )

    (SDK_DIR / "platform-tools").mkdir(exist_ok=True)

    return success

# --- Project, Signing & Build Logic ---
def sanitize_name(name):
    clean = "".join(c if c.isalnum() else "_" for c in name.strip())
    return clean or "MyWebApp"

def get_or_create_keystore(app_name, password, alias, log_widget):
    java_exe = list(JDK_DIR.glob("**/bin/java.exe"))[0]
    keytool_exe = java_exe.parent / "keytool.exe"
    ks_path = KEYSTORE_DIR / f"{sanitize_name(app_name)}_keystore.jks"

    if ks_path.exists():
        log_to_widget(log_widget, f"[OK] Found existing keystore: {ks_path.name}")
        return ks_path

    log_to_widget(log_widget, f"Generating new cryptographic Keystore: {ks_path.name}...")
    
    cmd = [
        str(keytool_exe), "-genkeypair", "-v",
        "-keystore", str(ks_path),
        "-alias", alias,
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
        "-storepass", password, "-keypass", password,
        "-dname", f"CN={sanitize_name(app_name)},O=AppForge,C=US"
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
    for line in process.stdout:
        log_to_widget(log_widget, line.rstrip())
    process.wait()

    if process.returncode == 0:
        log_to_widget(log_widget, "[SUCCESS] Offline Keystore generated.")
        return ks_path
    else:
        log_to_widget(log_widget, "[ERROR] Failed to generate Keystore.")
        return None

def create_android_project(app_name, html_file, icon_file, log_widget):
    safe_name = sanitize_name(app_name)
    package_name = f"com.portable.{safe_name.lower()}"
    project_dir = PROJECTS_DIR / safe_name

    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True)

    app_dir = project_dir / "app"
    src_dir = app_dir / "src" / "main"
    java_dir = src_dir / "java" / "com" / "portable" / safe_name.lower()
    res_dir = src_dir / "res"
    mipmap_dir = res_dir / "mipmap"
    assets_dir = src_dir / "assets"

    for d in [java_dir, mipmap_dir, assets_dir]:
        d.mkdir(parents=True, exist_ok=True)

    shutil.copy2(html_file, assets_dir / "index.html")
    if icon_file and os.path.isfile(icon_file):
        shutil.copy2(icon_file, mipmap_dir / "ic_launcher.png")

    settings_gradle_content = f"""pluginManagement {{
    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}
dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}
rootProject.name = "{safe_name}"
include(":app")
"""
    (project_dir / "settings.gradle").write_text(settings_gradle_content, encoding="utf-8")
    (project_dir / "local.properties").write_text(f"sdk.dir={str(SDK_DIR).replace(os.sep, '/')}\n", encoding="utf-8")
    (project_dir / "gradle.properties").write_text(
        "org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\n"
        "android.useAndroidX=true\n"
        "android.suppressUnsupportedCompileSdk=35\n", 
        encoding="utf-8"
    )

    (project_dir / "build.gradle").write_text("""
plugins {
    id 'com.android.application' version '8.5.0' apply false
}
""", encoding="utf-8")

    # FIX 1: Added buildTypes block with minifyEnabled false to stop R8 from breaking the app
    (app_dir / "build.gradle").write_text(f"""
plugins {{
    id 'com.android.application'
}}
android {{
    namespace '{package_name}'
    compileSdk 35
    buildToolsVersion '35.0.0'
    defaultConfig {{
        applicationId '{package_name}'
        minSdk 24
        targetSdk 35
        versionCode 1
        versionName '1.0'
    }}
    buildTypes {{
        release {{
            minifyEnabled false
        }}
        debug {{
            minifyEnabled false
        }}
    }}
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}
dependencies {{
}}
""", encoding="utf-8")

    (src_dir / "AndroidManifest.xml").write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:allowBackup="true"
        android:label="{app_name}"
        android:icon="@mipmap/ic_launcher"
        android:hardwareAccelerated="true"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""", encoding="utf-8")

    (java_dir / "MainActivity.java").write_text(f"""
package {package_name};
import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {{
    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        WebView webView = new WebView(this);
        setContentView(webView);
        
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        
        webView.loadUrl("file:///android_asset/index.html");
    }}
}}
""", encoding="utf-8")

    return project_dir

def execute_subprocess(cmd, cwd, env, log_widget, success_msg, error_msg):
    log_to_widget(log_widget, f"Executing: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
    for line in process.stdout:
        log_to_widget(log_widget, line.rstrip())
    process.wait()
    
    if process.returncode == 0:
        if success_msg: log_to_widget(log_widget, success_msg)
        return True
    else:
        if error_msg: log_to_widget(log_widget, error_msg)
        return False

def build_apk(project_dir, app_name, is_offline, is_release, ks_pass, ks_alias, log_widget):
    java_exe = list(JDK_DIR.glob("**/bin/java.exe"))[0]
    gradle_bat = list(GRADLE_DIR.glob("**/bin/gradle.bat"))[0]

    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_exe.parent.parent)
    env["ANDROID_HOME"] = str(SDK_DIR)
    env["PATH"] = str(java_exe.parent) + os.pathsep + env.get("PATH", "")
    
    # FIX 2: Force Gradle to use our portable cache folder so it never gets lost again
    env["GRADLE_USER_HOME"] = str(GRADLE_CACHE_DIR)

    task = "assembleRelease" if is_release else "assembleDebug"
    cmd = [str(gradle_bat), task]
    if is_offline:
        cmd.append("--offline")

    log_to_widget(log_widget, f"--- Phase 1: Gradle Build ({task}) ---")
    if not execute_subprocess(cmd, project_dir, env, log_widget, "[SUCCESS] Gradle build complete.", "[ERROR] Gradle build failed."):
        return None

    if not is_release:
        apk_path = project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
        if apk_path.exists():
            output_apk = OUTPUT_DIR / f"{sanitize_name(app_name)}_debug.apk"
            shutil.copy2(apk_path, output_apk)
            log_to_widget(log_widget, f"[SUCCESS] Debug APK Saved to: {output_apk}")
            return output_apk
        return None

    # --- Release Mode Pipeline (Zipalign & Sign) ---
    unsigned_apk = project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release-unsigned.apk"
    if not unsigned_apk.exists():
        log_to_widget(log_widget, "[ERROR] Could not find unsigned release APK.")
        return None

    # Step 1: Zipalign
    log_to_widget(log_widget, "\n--- Phase 2: Memory Optimization (Zipalign) ---")
    zipalign_exe = SDK_DIR / "build-tools" / "35.0.0" / "zipalign.exe"
    aligned_apk = project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release-aligned.apk"
    
    zip_cmd = [str(zipalign_exe), "-v", "-p", "4", str(unsigned_apk), str(aligned_apk)]
    if not execute_subprocess(zip_cmd, project_dir, env, log_widget, "[SUCCESS] APK Aligned.", "[ERROR] Zipalign failed."):
        return None

    # Step 2: Apksigner
    log_to_widget(log_widget, "\n--- Phase 3: Cryptographic Signing ---")
    ks_path = get_or_create_keystore(app_name, ks_pass, ks_alias, log_widget)
    if not ks_path:
        return None

    apksigner_bat = SDK_DIR / "build-tools" / "35.0.0" / "apksigner.bat"
    sign_cmd = [
        str(apksigner_bat), "sign",
        "--ks", str(ks_path),
        "--ks-pass", f"pass:{ks_pass}",
        "--ks-key-alias", ks_alias,
        "--key-pass", f"pass:{ks_pass}",
        str(aligned_apk)
    ]

    if not execute_subprocess(sign_cmd, project_dir, env, log_widget, "[SUCCESS] APK officially signed!", "[ERROR] Apksigner failed."):
        return None

    # Final Output
    final_output = OUTPUT_DIR / f"{sanitize_name(app_name)}_Release_Signed.apk"
    shutil.copy2(aligned_apk, final_output)
    log_to_widget(log_widget, f"\n[SUCCESS] Final Signed APK Saved to: {final_output}")
    return final_output


# --- Modern Dark UI ---
class DarkThemeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AppForge - Offline HTML to APK Builder")
        self.root.geometry("850x650")
        self.root.configure(bg="#1e1e1e")

        self.setup_styles()

        self.html_path = tk.StringVar()
        self.icon_path = tk.StringVar()
        self.app_name = tk.StringVar(value="My Web App")
        
        self.ks_alias = tk.StringVar(value="appforge_key")
        self.ks_pass = tk.StringVar(value="appforge123")
        
        self.offline_mode = tk.BooleanVar(value=False)
        self.release_mode = tk.BooleanVar(value=True) # Defaulting to True for you!

        self.sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = ttk.Frame(root, style="Content.TFrame")
        self.content.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.build_sidebar()
        self.build_content()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        bg_dark = "#1e1e1e"
        bg_panel = "#252526"
        fg_text = "#cccccc"
        accent = "#0e639c"

        style.configure("Content.TFrame", background=bg_dark)
        style.configure("Sidebar.TFrame", background=bg_panel)
        style.configure("TLabel", background=bg_dark, foreground=fg_text, font=("Segoe UI", 10))
        style.configure("Sidebar.TLabel", background=bg_panel, foreground=fg_text, font=("Segoe UI", 12, "bold"))
        
        style.configure("TButton", background="#333333", foreground=fg_text, borderwidth=1, focuscolor=bg_dark, font=("Segoe UI", 10))
        style.map("TButton", background=[("active", accent)])
        
        style.configure("Accent.TButton", background=accent, foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#1177bb")])

        style.configure("TEntry", fieldbackground="#3c3c3c", foreground="#ffffff", bordercolor="#3c3c3c", insertcolor="#ffffff")
        style.configure("TCheckbutton", background=bg_dark, foreground=fg_text, focuscolor=bg_dark)

    def build_sidebar(self):
        ttk.Label(self.sidebar, text="APP FORGE", style="Sidebar.TLabel").pack(pady=(20, 30))
        
        ttk.Button(self.sidebar, text="1. Setup Engines", command=self.start_setup).pack(fill="x", padx=10, pady=5)
        ttk.Button(self.sidebar, text="2. Build APK", style="Accent.TButton", command=self.start_build).pack(fill="x", padx=10, pady=20)
        
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=10, pady=10)
        ttk.Button(self.sidebar, text="Clear Logs", command=lambda: self.log.config(state="normal") or self.log.delete(1.0, tk.END) or self.log.config(state="disabled")).pack(fill="x", padx=10, pady=5)

    def build_content(self):
        grid_frame = ttk.Frame(self.content, style="Content.TFrame")
        grid_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(grid_frame, text="App Name:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(grid_frame, textvariable=self.app_name, width=45).grid(row=0, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(grid_frame, text="index.html File:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(grid_frame, textvariable=self.html_path, width=45).grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ttk.Button(grid_frame, text="Browse", command=self.choose_html).grid(row=1, column=2)

        ttk.Label(grid_frame, text="App Icon (PNG):").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(grid_frame, textvariable=self.icon_path, width=45).grid(row=2, column=1, padx=10, pady=5, sticky="w")
        ttk.Button(grid_frame, text="Browse", command=self.choose_icon).grid(row=2, column=2)

        ttk.Separator(grid_frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        # Signing Specs
        ttk.Label(grid_frame, text="Keystore Alias:").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(grid_frame, textvariable=self.ks_alias, width=20).grid(row=4, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(grid_frame, text="Keystore Password:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(grid_frame, textvariable=self.ks_pass, width=20, show="*").grid(row=5, column=1, padx=10, pady=5, sticky="w")

        # Toggles
        toggle_frame = ttk.Frame(self.content, style="Content.TFrame")
        toggle_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(toggle_frame, text="Offline Build", variable=self.offline_mode).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(toggle_frame, text="Release Mode (Sign & Zipalign APK)", variable=self.release_mode).pack(side="left")

        # Logs
        self.log = tk.Text(self.content, bg="#111111", fg="#4af626", font=("Consolas", 9), state="disabled", wrap="word", relief="flat", padx=10, pady=10)
        self.log.pack(fill="both", expand=True)

    def choose_html(self):
        path = filedialog.askopenfilename(filetypes=[("HTML files", "*.html")])
        if path: self.html_path.set(path)

    def choose_icon(self):
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if path: self.icon_path.set(path)

    def start_setup(self):
        threading.Thread(target=self.run_setup, daemon=True).start()

    def run_setup(self):
        self.log.config(state="normal"); self.log.delete(1.0, tk.END); self.log.config(state="disabled")
        log_to_widget(self.log, "=== STARTING ENGINE SETUP ===")
        
        if not setup_jdk(self.log) or not setup_gradle(self.log) or not setup_android_sdk(self.log):
            messagebox.showerror("Setup Failed", "One or more engines failed to setup. Check logs.")
            return
        
        log_to_widget(self.log, "\n=== ALL ENGINES READY ===")
        messagebox.showinfo("Success", "Setup completed successfully! You can now build APKs.")

    def start_build(self):
        threading.Thread(target=self.run_build, daemon=True).start()

    def run_build(self):
        html = self.html_path.get().strip()
        icon = self.icon_path.get().strip()
        name = self.app_name.get().strip()
        ks_alias = self.ks_alias.get().strip()
        ks_pass = self.ks_pass.get().strip()

        if not html or not os.path.isfile(html):
            messagebox.showerror("Error", "Please select a valid index.html file.")
            return
        if not name:
            messagebox.showerror("Error", "Please enter an app name.")
            return
        if self.release_mode.get() and (not ks_alias or len(ks_pass) < 6):
            messagebox.showerror("Error", "Release mode requires an Alias and a Password (minimum 6 characters) for the Keystore.")
            return

        self.log.config(state="normal"); self.log.delete(1.0, tk.END); self.log.config(state="disabled")
        log_to_widget(self.log, f"=== BUILDING: {name} ===")
        
        try:
            log_to_widget(self.log, "Generating Android Project Structure...")
            project_dir = create_android_project(name, html, icon, self.log)
            
            apk = build_apk(
                project_dir, name, 
                self.offline_mode.get(), self.release_mode.get(), 
                ks_pass, ks_alias, self.log
            )
            
            if apk:
                messagebox.showinfo("Success", f"APK successfully generated!\nSaved at:\n{apk}")
            else:
                messagebox.showerror("Build Failed", "Check the log window for errors.")
        except Exception as e:
            messagebox.showerror("Fatal Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = DarkThemeApp(root)
    root.mainloop()
