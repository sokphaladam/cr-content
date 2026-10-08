// Shorts Studio desktop app: opens the Next.js UI in a native window and runs the Python video engine beside it.
//
// Dev (`npm run dev`):   the engine is app.py from the project's .venv; data stays in the project folder.
// Release (installer):  the engine is the PyInstaller build bundled under resources/engine; data (drafts, output,
//                       uploads, cache, assets, .env) goes to the user's app-data folder.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::error::Error;
use std::fs::{self, File};
use std::io::Write;
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::webview::DownloadEvent;
use tauri::{AppHandle, Manager, RunEvent, Webview, WebviewUrl, WebviewWindowBuilder};

/// The running engine process, killed when the app exits.
struct Engine(Mutex<Option<Child>>);

fn free_port() -> std::io::Result<u16> {
    Ok(TcpListener::bind("127.0.0.1:0")?.local_addr()?.port())
}

/// Folder for everything the engine writes.
fn data_dir(app: &AppHandle) -> Result<PathBuf, Box<dyn Error>> {
    let dir = if cfg!(debug_assertions) {
        Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf()
    } else {
        app.path().app_data_dir()?
    };
    fs::create_dir_all(&dir)?;
    Ok(dir)
}

fn engine_command(app: &AppHandle, data: &Path) -> Result<Command, Box<dyn Error>> {
    if cfg!(debug_assertions) {
        let python = [".venv/Scripts/python.exe", ".venv/bin/python"]
            .iter()
            .map(|p| data.join(p))
            .find(|p| p.exists())
            .ok_or("Python virtualenv not found. In the project folder run: python -m venv .venv, then install requirements.txt")?;
        let mut cmd = Command::new(python);
        cmd.arg(data.join("app.py"));
        return Ok(cmd);
    }
    let resources = app.path().resource_dir()?;
    // First run: give the user a .env to fill in their API keys.
    let env_file = data.join(".env");
    if !env_file.exists() {
        let _ = fs::copy(resources.join(".env.example"), &env_file);
    }
    let exe = if cfg!(windows) { "engine.exe" } else { "engine" };
    Ok(Command::new(resources.join("engine").join(exe)))
}

fn start_engine(app: &AppHandle, data: &Path, port: u16) -> Result<Child, Box<dyn Error>> {
    let mut cmd = engine_command(app, data)?;
    // --parent-pid: the engine exits when this app does, so it can't outlive the app even if the app crashes.
    cmd.args(["--no-browser", "--port", &port.to_string(), "--parent-pid", &std::process::id().to_string()])
        .current_dir(data)
        .env("CRCONTENT_DATA_DIR", data)
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::null());
    if !cfg!(debug_assertions) {
        // No console in release: keep the engine's output in a log file.
        let log = File::create(data.join("engine.log"))?;
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

/// Downloads (video, thumbnail, song...) ask where to save, like a browser's "Save as", instead of going silently
/// to the Downloads folder. The page gets a `desktop-download` event to show the result.
fn on_download(webview: Webview, event: DownloadEvent<'_>) -> bool {
    match event {
        DownloadEvent::Requested { destination, .. } => {
            // WebView2 proposes Downloads\<name from the server>; offer that as the default.
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

fn setup(app: &mut tauri::App) -> Result<(), Box<dyn Error>> {
    let handle = app.handle().clone();
    let data = data_dir(&handle)?;
    let port = free_port()?;
    match start_engine(&handle, &data, port) {
        Ok(child) => {
            app.manage(Engine(Mutex::new(Some(child))));
        }
        // Still open the window: the UI explains that the engine is unreachable and points to engine.log.
        Err(e) => {
            eprintln!("Couldn't start the video engine: {e}");
            if let Ok(mut log) = File::create(data.join("engine.log")) {
                let _ = writeln!(log, "Couldn't start the video engine: {e}");
            }
        }
    }

    WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
        .title("Shorts Studio")
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
        .setup(setup)
        .build(tauri::generate_context!())
        .expect("error while building Shorts Studio");

    app.run(|app, event| {
        if let RunEvent::Exit = event {
            if let Some(engine) = app.try_state::<Engine>() {
                if let Some(mut child) = engine.0.lock().unwrap().take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    });
}
