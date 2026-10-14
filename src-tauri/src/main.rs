// Shorts Studio desktop app: opens the Next.js UI in a native window and runs the Python video engine beside it.
//
// Dev (`npm run dev`):   the engine is app.py from the project's .venv.
// Release (installer):  the engine is the PyInstaller build bundled under resources/engine.
// Either way the engine keeps the library (drafts, videos, uploads, cache, assets, keys) in the folders chosen in
// Settings (crcontent/locations.py); this app only gives it a working folder and, in release, engine.log.
//
// Scheduled uploads need the engine running, so closing the window only hides it: the app stays in the tray
// (Quit there stops it; the menu bar on macOS), can start at sign-in (`--background`: straight to the tray; a Run
// registry value on Windows, a LaunchAgent on macOS), and runs once: opening it again shows the running window
// instead of starting a second engine that would post the same videos twice.
//
// Updates: the page checks GitHub Releases (tauri-plugin-updater; latest.json signed with the project's key, see
// tauri.conf.json plugins.updater) through check_update, and install_update downloads, stops the engine and restarts.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::error::Error;
use std::fs::{self, File};
use std::io::Write;
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::menu::{CheckMenuItem, Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::webview::DownloadEvent;
use tauri::{AppHandle, Manager, RunEvent, Webview, WebviewUrl, WebviewWindowBuilder, WindowEvent};

/// Launched at sign-in: start in the tray, without a window.
const BACKGROUND_ARG: &str = "--background";
#[cfg(windows)]
const RUN_KEY: &str = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run";
#[cfg(windows)]
const RUN_VALUE: &str = "Shorts Studio";
/// The tray menu's name for starting at sign-in.
const AUTOSTART_LABEL: &str = if cfg!(target_os = "macos") { "Open at Login" } else { "Start with Windows" };

/// The tray menu's "Start with Windows" tick, kept in step when Settings changes it.
struct AutostartItem(CheckMenuItem<tauri::Wry>);

/// The running engine process, killed when the app exits.
struct Engine(Mutex<Option<Child>>);

/// The update found by the last check_update, ready for install_update.
struct PendingUpdate(Mutex<Option<tauri_plugin_updater::Update>>);

fn free_port() -> std::io::Result<u16> {
    Ok(TcpListener::bind("127.0.0.1:0")?.local_addr()?.port())
}

/// The engine's working folder: the project in dev, else the app's own folder (the same one locations.py uses,
/// where engine.log is kept). Never the library itself, so the library can be moved while the engine runs.
fn work_dir(app: &AppHandle) -> Result<PathBuf, Box<dyn Error>> {
    let dir = if cfg!(debug_assertions) {
        Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf()
    } else {
        app.path().app_data_dir()?
    };
    fs::create_dir_all(&dir)?;
    Ok(dir)
}

fn engine_command(app: &AppHandle, work: &Path) -> Result<Command, Box<dyn Error>> {
    if cfg!(debug_assertions) {
        let python = [".venv/Scripts/python.exe", ".venv/bin/python"]
            .iter()
            .map(|p| work.join(p))
            .find(|p| p.exists())
            .ok_or("Python virtualenv not found. In the project folder run: python -m venv .venv, then install requirements.txt")?;
        let mut cmd = Command::new(python);
        cmd.arg(work.join("app.py"));
        return Ok(cmd);
    }
    let exe = if cfg!(windows) { "engine.exe" } else { "engine" };
    Ok(Command::new(app.path().resource_dir()?.join("engine").join(exe)))
}

/// The engine's PATH: the FFmpeg bundled with the installer first (resources/ffmpeg, from scripts/fetch_ffmpeg.py),
/// then the usual PATH. On macOS also Homebrew's folders, which apps opened from Finder don't get.
fn engine_path(app: &AppHandle) -> std::ffi::OsString {
    let mut dirs: Vec<PathBuf> = Vec::new();
    if !cfg!(debug_assertions) {
        if let Ok(res) = app.path().resource_dir() {
            dirs.push(res.join("ffmpeg"));
        }
    }
    dirs.extend(std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default()));
    if cfg!(target_os = "macos") {
        for extra in ["/opt/homebrew/bin", "/usr/local/bin"] {
            if !dirs.iter().any(|d| d == Path::new(extra)) {
                dirs.push(PathBuf::from(extra));
            }
        }
    }
    std::env::join_paths(dirs).unwrap_or_default()
}

fn start_engine(app: &AppHandle, work: &Path, port: u16) -> Result<Child, Box<dyn Error>> {
    let mut cmd = engine_command(app, work)?;
    // --parent-pid: the engine exits when this app does, so it can't outlive the app even if the app crashes.
    // (When the engine restarts itself after the folders change, the new one gets the same arguments.)
    cmd.args(["--no-browser", "--port", &port.to_string(), "--parent-pid", &std::process::id().to_string()])
        .current_dir(work)
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::null());
    cmd.env("PATH", engine_path(app));
    if !cfg!(debug_assertions) {
        // No console in release: keep the engine's output in a log file.
        let log = File::create(work.join("engine.log"))?;
        cmd.stdout(log.try_clone()?).stderr(log);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
    }
    Ok(cmd.spawn()?)
}

#[cfg(windows)]
fn reg(args: &[&str]) -> bool {
    use std::os::windows::process::CommandExt;
    let mut cmd = Command::new("reg");
    cmd.args(args).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
    cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    cmd.status().map(|s| s.success()).unwrap_or(false)
}

/// Is the app set to start (in the tray) when you sign in to Windows?
#[cfg(windows)]
fn autostart_enabled() -> bool {
    reg(&["query", RUN_KEY, "/v", RUN_VALUE])
}

#[cfg(windows)]
fn set_autostart_enabled(on: bool) -> Result<(), String> {
    let ok = if on {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        let command = format!("\"{}\" {BACKGROUND_ARG}", exe.display());
        reg(&["add", RUN_KEY, "/v", RUN_VALUE, "/t", "REG_SZ", "/d", &command, "/f"])
    } else {
        !autostart_enabled() || reg(&["delete", RUN_KEY, "/v", RUN_VALUE, "/f"])
    };
    if ok { Ok(()) } else { Err("Windows didn't accept the change.".into()) }
}

/// macOS: a LaunchAgent in ~/Library/LaunchAgents starts the app (in the menu bar) when you log in.
#[cfg(not(windows))]
fn launch_agent() -> Option<PathBuf> {
    let home = std::env::var_os("HOME")?;
    Some(PathBuf::from(home).join("Library/LaunchAgents/com.crcontent.shorts-studio.plist"))
}

#[cfg(not(windows))]
fn autostart_enabled() -> bool {
    launch_agent().is_some_and(|p| p.exists())
}

#[cfg(not(windows))]
fn set_autostart_enabled(on: bool) -> Result<(), String> {
    let plist = launch_agent().ok_or("Your home folder wasn't found.")?;
    if !on {
        return match fs::remove_file(&plist) {
            Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(e.to_string()),
            _ => Ok(()),
        };
    }
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let exe = exe.display().to_string().replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;");
    let body = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.crcontent.shorts-studio</string>
  <key>ProgramArguments</key>
  <array>
    <string>{exe}</string>
    <string>{BACKGROUND_ARG}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>ProcessType</key>
  <string>Interactive</string>
</dict>
</plist>
"#
    );
    if let Some(dir) = plist.parent() {
        fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    fs::write(&plist, body).map_err(|e| e.to_string())
}

/// Settings → Desktop app: start at sign-in, in the tray (menu bar on macOS).
#[tauri::command]
fn get_autostart() -> bool {
    autostart_enabled()
}

#[tauri::command]
fn set_autostart(app: AppHandle, enabled: bool) -> Result<bool, String> {
    set_autostart_enabled(enabled)?;
    if let Some(item) = app.try_state::<AutostartItem>() {
        let _ = item.0.set_checked(enabled);
    }
    Ok(autostart_enabled())
}

fn show_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn build_tray(app: &tauri::App) -> Result<(), Box<dyn Error>> {
    let open = MenuItem::with_id(app, "open", "Open Shorts Studio", true, None::<&str>)?;
    let autostart = CheckMenuItem::with_id(app, "autostart", AUTOSTART_LABEL, true, autostart_enabled(), None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit (stops scheduled uploads)", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &autostart, &PredefinedMenuItem::separator(app)?, &quit])?;
    app.manage(AutostartItem(autostart));
    TrayIconBuilder::with_id("main")
        .icon(app.default_window_icon().cloned().ok_or("no app icon")?)
        .tooltip("Shorts Studio: running in the background for scheduled uploads")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show_window(app),
            "autostart" => {
                let on = !autostart_enabled();
                let _ = set_autostart_enabled(on);
                if let Some(item) = app.try_state::<AutostartItem>() {
                    let _ = item.0.set_checked(autostart_enabled());
                }
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                show_window(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

/// Settings → Storage: a native folder picker (the page can't get full paths from the browser's own pickers).
#[tauri::command]
async fn pick_folder(title: String, start: Option<String>) -> Option<String> {
    let mut dialog = rfd::FileDialog::new().set_title(title);
    if let Some(dir) = start.map(PathBuf::from).filter(|d| d.is_dir()) {
        dialog = dialog.set_directory(dir);
    }
    dialog.pick_folder().map(|p| p.display().to_string())
}

/// Downloads (video, thumbnail, song...) ask where to save, like a browser's "Save as", instead of going silently
/// to the Downloads folder. The page gets a `desktop-download` event to show the result.
fn on_download(webview: Webview, event: DownloadEvent<'_>) -> bool {
    match event {
        DownloadEvent::Requested { destination, .. } => {
            // The webview proposes Downloads/<name from the server>; offer that as the default.
            let mut dialog = rfd::FileDialog::new().set_title("Save as");
            if let Some(name) = destination.file_name() {
                dialog = dialog.set_file_name(name.to_string_lossy());
                if let Some(ext) = destination.extension() {
                    let ext = ext.to_string_lossy().to_string();
                    dialog = dialog.add_filter(ext.to_uppercase(), &[ext.as_str()]);
                }
            }
            if let Some(dir) = destination.parent().filter(|d| d.is_dir()) {
                dialog = dialog.set_directory(dir);
            }
            match dialog.save_file() {
                Some(path) => {
                    *destination = path;
                    true
                }
                None => false, // cancelled
            }
        }
        DownloadEvent::Finished { path, success, .. } => {
            let detail = serde_json::json!({
                "success": success,
                "path": path.as_ref().map(|p| p.display().to_string()),
                "name": path.as_ref().and_then(|p| p.file_name()).map(|n| n.to_string_lossy().to_string()),
            });
            let _ = webview.eval(format!(
                "window.dispatchEvent(new CustomEvent('desktop-download', {{ detail: {detail} }}))"
            ));
            true
        }
        _ => true,
    }
}

fn stop_engine(app: &AppHandle) {
    if let Some(engine) = app.try_state::<Engine>() {
        if let Some(mut child) = engine.0.lock().unwrap().take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

/// Settings → About: this app's version.
#[tauri::command]
fn app_version(app: AppHandle) -> String {
    app.package_info().version.to_string()
}

/// Is there a newer version on GitHub? Its version, notes and date, or null. Remembered for install_update.
#[tauri::command]
async fn check_update(app: AppHandle) -> Result<serde_json::Value, String> {
    use tauri_plugin_updater::UpdaterExt;
    let update = app.updater().map_err(|e| e.to_string())?.check().await.map_err(|e| e.to_string())?;
    let info = update.as_ref().map(|u| {
        serde_json::json!({
            "version": u.version,
            "current": u.current_version,
            "notes": u.body.clone().unwrap_or_default(),
            "date": u.date.map(|d| d.to_string()).unwrap_or_default(),
        })
    });
    *app.state::<PendingUpdate>().0.lock().unwrap() = update;
    Ok(info.unwrap_or(serde_json::Value::Null))
}

/// Download the update found by check_update (the page gets `desktop-update` progress events), stop the engine so
/// its files can be replaced, install and restart. On Windows the installer takes over and the app closes.
#[tauri::command]
async fn install_update(app: AppHandle) -> Result<(), String> {
    let update = app.state::<PendingUpdate>().0.lock().unwrap().take().ok_or("Check for updates first.")?;
    let window = app.get_webview_window("main");
    let (mut done, mut shown) = (0u64, -1i64);
    let bytes = update
        .download(
            |chunk, total| {
                done += chunk as u64;
                let pct = total.map(|t| (done * 100 / t.max(1)) as i64).unwrap_or(-1);
                if pct != shown {
                    shown = pct;
                    if let Some(w) = &window {
                        let detail = serde_json::json!({ "downloaded": done, "total": total });
                        let _ = w.eval(format!("window.dispatchEvent(new CustomEvent('desktop-update', {{ detail: {detail} }}))"));
                    }
                }
            },
            || {},
        )
        .await
        .map_err(|e| e.to_string())?;
    stop_engine(&app);
    update.install(bytes).map_err(|e| e.to_string())?;
    app.restart();
}

fn setup(app: &mut tauri::App) -> Result<(), Box<dyn Error>> {
    let handle = app.handle().clone();
    let work = work_dir(&handle)?;
    let port = free_port()?;
    match start_engine(&handle, &work, port) {
        Ok(child) => {
            app.manage(Engine(Mutex::new(Some(child))));
        }
        // Still open the window: the UI explains that the engine is unreachable and points to engine.log.
        Err(e) => {
            eprintln!("Couldn't start the video engine: {e}");
            if let Ok(mut log) = File::create(work.join("engine.log")) {
                let _ = writeln!(log, "Couldn't start the video engine: {e}");
            }
        }
    }

    build_tray(app)?;
    let background = std::env::args().any(|a| a == BACKGROUND_ARG);
    WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
        .title("Shorts Studio")
        .visible(!background)
        .inner_size(1440.0, 900.0)
        .min_inner_size(960.0, 640.0)
        .center()
        .initialization_script(&format!("window.__ENGINE_URL__ = \"http://127.0.0.1:{port}\";"))
        .on_download(on_download)
        .build()?;
    Ok(())
}

fn main() {
    let app = tauri::Builder::default()
        // must come first: a second launch (a click on the shortcut while it runs in the tray) shows this one
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| show_window(app)))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(PendingUpdate(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![pick_folder, get_autostart, set_autostart, app_version, check_update, install_update])
        .on_window_event(|window, event| {
            // closing the window keeps the app (and its upload schedule) running in the tray
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .setup(setup)
        .build(tauri::generate_context!())
        .expect("error while building Shorts Studio");

    app.run(|app, event| match event {
        RunEvent::Exit => stop_engine(app),
        // macOS: a click on the Dock icon brings back the hidden window
        #[cfg(target_os = "macos")]
        RunEvent::Reopen { .. } => show_window(app),
        _ => {}
    });
}
