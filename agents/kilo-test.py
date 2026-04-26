from kilo_code_agent import handle_read, handle_write, handle_edit

def test_kilo_capabilities():
    """Test processing read/write operations"""
    # Sample test file
    test_content = "print('Kilo Code Integration Test')"
    
    # Initialize with content
    handle_write("test_kilo.txt", test_content)
    
    # Read back and verify
    read_content = handle_read("test_kilo.txt")
    
    print(f"Original: {test_content}")
    print(f"Read back: {read_content}")
    print("Test completed")

if __name__ == "__main__":
    test_kilo_capabilities()