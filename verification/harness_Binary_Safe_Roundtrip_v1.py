import os
import tempfile
import logging
import shutil

# --- Configuration ---
# Set up basic logging to show the harness's progress.
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# --- Mock Implementations ---
# These functions simulate the core logic of the Bundle File Tool,
# implementing the "Strict Fix" (binary I/O) from the analysis report.

def bundle(source_root, bundle_path):
    """
    Mock bundle function.

    Walks a source directory and creates a simple, binary-safe archive.
    The format for each file is:
    - 4 bytes: Length of the relative file path (as an integer).
    - N bytes: The relative file path (UTF-8 encoded).
    - 8 bytes: Length of the file content (as an integer).
    - M bytes: The raw file content (as bytes).

    This process is performed in binary mode to prevent any newline
    translation, ensuring data integrity.
    """
    logging.info(f"Bundling directory '{source_root}' to '{bundle_path}'...")
    try:
        with open(bundle_path, 'wb') as bundle_file:
            for dirpath, _, filenames in os.walk(source_root):
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    
                    # Get the file path relative to the source root.
                    relative_path = os.path.relpath(full_path, source_root)
                    relative_path_bytes = relative_path.encode('utf-8')
                    
                    # Write metadata: path length, path.
                    bundle_file.write(len(relative_path_bytes).to_bytes(4, 'big'))
                    bundle_file.write(relative_path_bytes)
                    
                    # Write metadata: content length, content.
                    # Reading the file in binary mode ('rb') is critical.
                    with open(full_path, 'rb') as content_file:
                        content = content_file.read()
                        bundle_file.write(len(content).to_bytes(8, 'big'))
                        bundle_file.write(content)
                        logging.info(f"  - Added '{relative_path}' ({len(content)} bytes)")
        logging.info("Bundling complete.")
        return True
    except IOError as e:
        logging.error(f"Error during bundling: {e}")
        return False

def unbundle(bundle_path, destination_root):
    """
    Mock unbundle function.

    Reads the binary-safe archive and restores the files and directory
    structure. This process is also performed entirely in binary mode.
    """
    logging.info(f"Unbundling file '{bundle_path}' to '{destination_root}'...")
    try:
        with open(bundle_path, 'rb') as bundle_file:
            while True:
                # Read path length. If it's empty, we've reached the end of the file.
                path_len_bytes = bundle_file.read(4)
                if not path_len_bytes:
                    break
                path_len = int.from_bytes(path_len_bytes, 'big')
                
                # Read path and content length.
                relative_path = bundle_file.read(path_len).decode('utf-8')
                content_len = int.from_bytes(bundle_file.read(8), 'big')
                
                # Read content.
                content = bundle_file.read(content_len)
                
                # Recreate the file at the destination.
                dest_path = os.path.join(destination_root, relative_path)
                
                # Ensure the target directory exists.
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Writing the file in binary mode ('wb') is critical.
                with open(dest_path, 'wb') as content_file:
                    content_file.write(content)
                logging.info(f"  - Extracted '{relative_path}' ({len(content)} bytes)")
        logging.info("Unbundling complete.")
        return True
    except (IOError, ValueError) as e:
        logging.error(f"Error during unbundling: {e}")
        return False

# --- Test Harness ---

def run_binary_safe_roundtrip_harness():
    """
    A self-contained, hermetic test harness.

    It uses a temporary directory to ensure that each run is isolated and
    leaves no artifacts on the filesystem, as recommended in the report.
    """
    logging.info("--- Starting Binary-Safe Roundtrip Test Harness ---")
    
    # The 'with' statement guarantees the temporary directory and all its
    # contents are cleaned up, even if errors occur.
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info(f"Created temporary directory: {temp_dir}")
        
        source_dir = os.path.join(temp_dir, 'source_project')
        dest_dir = os.path.join(temp_dir, 'destination_project')
        bundle_path = os.path.join(temp_dir, 'archive.bundle')
        
        os.makedirs(source_dir)
        os.makedirs(dest_dir)

        # --- Test Cases ---
        # Define a dictionary of test cases: {filename: content_bytes}
        test_cases = {
            "mixed_newlines.txt": b'line one\nline two\r\nline three\r',
            "empty_file.txt": b'',
            "binary_data.bin": b'\x00\xDE\xAD\xBE\xEF\xFF\x8A',
            "utf8_chars.txt": "Testing UTF-8: éàçüö".encode('utf-8'),
            os.path.join("nested", "file.txt"): b'A file in a nested directory.'
        }

        # 1. SETUP: Create the source files for our test cases.
        logging.info("Setting up source files...")
        for rel_path, content in test_cases.items():
            file_path = os.path.join(source_dir, rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(content)
        
        # 2. EXECUTE: Run the bundle and unbundle operations.
        bundle(source_dir, bundle_path)
        unbundle(bundle_path, dest_dir)
        
        # 3. VERIFY: Assert that the unbundled content is identical to the original.
        logging.info("Verifying restored files...")
        all_passed = True
        for rel_path, original_content in test_cases.items():
            restored_path = os.path.join(dest_dir, rel_path)
            
            try:
                # Verify file existence.
                assert os.path.exists(restored_path), f"File '{restored_path}' does not exist."
                
                # Read back the content in binary mode.
                with open(restored_path, 'rb') as f:
                    restored_content = f.read()
                
                # The core assertion: byte-for-byte comparison.
                assert original_content == restored_content, f"Content mismatch for '{rel_path}'."
                
                logging.info(f" Verification for '{rel_path}' successful.")
                
            except AssertionError as e:
                logging.error(f"[FAIL] Verification for '{rel_path}' failed: {e}")
                logging.error(f"  - Original content:  {original_content!r}")
                logging.error(f"  - Restored content: {restored_content!r}")
                all_passed = False

        # --- Final Result ---
        print("-" * 50)
        if all_passed:
            logging.info("✅ SUCCESS: All test cases passed the binary-safe roundtrip.")
        else:
            logging.error("❌ FAILURE: One or more test cases failed.")
        print("-" * 50)

    logging.info("--- Test Harness Finished: Temporary directory cleaned up. ---")


if __name__ == "__main__":
    # This allows the script to be run directly from the command line.
    run_binary_safe_roundtrip_harness()
