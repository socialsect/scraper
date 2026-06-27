"""Test if the LiveDisplay monkey-patching works."""

from utils import display as display_module

print("Original LiveDisplay:", display_module.LiveDisplay)

# Simulate what server.py does
original_class = display_module.LiveDisplay

class InterceptedDisplay(original_class):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("✓ InterceptedDisplay.__init__ called!")
        
    def update_stats(self, **kwargs):
        print(f"✓ InterceptedDisplay.update_stats called with: {kwargs}")
        super().update_stats(**kwargs)

# Replace the class
display_module.LiveDisplay = InterceptedDisplay

print("Patched LiveDisplay:", display_module.LiveDisplay)

# Now test it
print("\nCreating LiveDisplay instance...")
display = display_module.LiveDisplay(query="test", total_urls=10, backend="scrapling")

print("\nCalling update_stats...")
with display:
    display.update_stats(pages=5, new_emails=3, total_emails=10)
    
print("\nDone! If you see ✓ messages above, the patch works.")
