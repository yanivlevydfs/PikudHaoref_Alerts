import sys
import os

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.services.oref_client import get_working_proxy

def test_proxy_loading():
    print("Testing get_working_proxy...")
    try:
        proxy = get_working_proxy()
        print(f"Result: {proxy}")
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_proxy_loading()
