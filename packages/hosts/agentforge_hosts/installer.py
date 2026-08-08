import os
import sys
import shutil

def run_installer() -> None:
    print("==================================================")
    print("🎬 AgentForge DaVinci Resolve Script Panel Installer")
    print("==================================================")

    # 1. Deterministic candidates for Resolve utility scripts path on Linux
    home = os.environ.get("HOME", "/home/shadow")
    candidates = [
        os.path.join(home, ".local/share/DaVinciResolve/Fusion/Scripts/Utility"),
        "/opt/resolve/Fusion/Scripts/Utility",
        "/home/resolve/Fusion/Scripts/Utility"
    ]
    
    selected_dir = None
    for path in candidates:
        if os.path.exists(path):
            selected_dir = path
            break
            
    # Fallback to create the local home directory path if DaVinci Resolve directories exist or standard path is desired
    if not selected_dir:
        # Check if the parent Resolve configuration folder exists
        resolve_parent = os.path.join(home, ".local/share/DaVinciResolve")
        if os.path.exists(resolve_parent):
            local_path = os.path.join(home, ".local/share/DaVinciResolve/Fusion/Scripts/Utility")
            os.makedirs(local_path, exist_ok=True)
            selected_dir = local_path

    if not selected_dir:
        # Fallback to create local folder in user home anyway so testing is easy
        local_path = os.path.join(home, ".local/share/DaVinciResolve/Fusion/Scripts/Utility")
        try:
            os.makedirs(local_path, exist_ok=True)
            selected_dir = local_path
        except Exception as e:
            print(f"❌ Error: Resolve installation script folders not detected and could not create fallback. {e}", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Resolve installation script path detected at:\n  {selected_dir}")

    # 2. Source file path
    src_panel = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../apps/studio/agentforge_studio/agentforge_panel.py"))
    dest_panel = os.path.join(selected_dir, "agentforge_panel.py")

    if not os.path.exists(src_panel):
        print(f"❌ Error: Source panel script not found at {src_panel}", file=sys.stderr)
        sys.exit(1)

    try:
        shutil.copy(src_panel, dest_panel)
        print("✓ AgentForge Resolve script installed successfully.")
        print("\n🎉 SUCCESS")
        print("Launch from Workspace → Scripts → agentforge_panel inside DaVinci Resolve.")
    except Exception as e:
        print(f"❌ Error copying panel script: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_installer()
