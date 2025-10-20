import base64
import os
import tempfile
import hashlib

def create_mock_binary_file(directory):
    """Creates a small binary file with known content for testing."""
    file_path = os.path.join(directory, 'mock_binary_file.bin')
    # Create some non-text binary data.
    # The byte sequence includes values that are not valid in UTF-8.
    binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    with open(file_path, 'wb') as f:
        f.write(binary_content)
    print(f"✅ Created mock binary file at: {file_path}")
    return file_path, binary_content

def simulate_bundling_binary(content: bytes) -> str:
    """
    Simulates the core logic of the bundler: encoding binary content to
    a base64 string. This is the part that likely fails in the real code.
    """
    encoded_string = base64.b64encode(content).decode('ascii')
    print("✅ Content encoded to base64 for bundling.")
    return encoded_string

def simulate_unbundling_binary(encoded_string: str) -> bytes:
    """
    Simulates the unbundling process: decoding a base64 string
    back into its original binary content.
    """
    decoded_bytes = base64.b64decode(encoded_string.encode('ascii'))
    print("✅ Base64 string decoded back to binary content.")
    return decoded_bytes

def verify_roundtrip(original_content: bytes, roundtrip_content: bytes):
    """
    Compares the original binary content with the content after a full
    encode/decode cycle.
    """
    original_hash = hashlib.sha256(original_content).hexdigest()
    roundtrip_hash = hashlib.sha256(roundtrip_content).hexdigest()

    print("\n--- Verification ---")
    print(f"Original SHA256 Hash:    {original_hash}")
    print(f"Roundtrip SHA256 Hash:   {roundtrip_hash}")

    if original_content == roundtrip_content:
        print("\n🏆 SUCCESS: The round-tripped binary content is identical to the original.")
        return True
    else:
        print("\n❌ FAILURE: The round-tripped content does not match the original.")
        print(f"Original length: {len(original_content)} bytes")
        print(f"Roundtrip length: {len(roundtrip_content)} bytes")
        return False

def main():
    """Main execution block for the test harness."""
    print("--- Starting Binary Safe Roundtrip Test Harness ---")
    # Use a temporary directory to avoid cluttering the project
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. Create the original file
            file_path, original_binary_content = create_mock_binary_file(temp_dir)

            # 2. Simulate the bundling process (reading and encoding)
            base64_string = simulate_bundling_binary(original_binary_content)
            print(f"   - Generated Base64: '{base64_string[:30]}...'")


            # 3. Simulate the unbundling process (decoding)
            roundtrip_binary_content = simulate_unbundling_binary(base64_string)

            # 4. Verify the integrity of the data
            verify_roundtrip(original_binary_content, roundtrip_binary_content)

        except Exception as e:
            print(f"\n❌ An error occurred during the test: {e}")
        finally:
            print("\n--- Test Harness Finished ---")


if __name__ == "__main__":
    main()
