import os
from components.filewatcher import FileWatcher


def update_callback(file_path):
    print(f"DEBUG: File change detected at {file_path}")


if __name__ == "__main__":

    # Get the current directory where test.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    target_file = os.path.join(current_dir, "test_files/test.py")

    watcher = FileWatcher(target_file)

    try:
        print(f"Starting to watch file: {target_file}")
        watcher.start_watching(update_callback)

        while True:
            pass

    except KeyboardInterrupt:
        print("\nStopping file watcher...")
        watcher.stop_watching()
        print("File watcher stopped.")
