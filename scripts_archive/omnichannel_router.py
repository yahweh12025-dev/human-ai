import random

class OmniChannelRouter:
    def __init__(self):
        # Mapping intent to a list of (provider_type, provider_name)
        # provider_type: 'api' or 'browser'
        self.routing_map = {
            "reasoning": [
                ("browser", "gemini"),
                ("browser", "claude"),
                ("api", "gemini-2.0-flash-thinking"),
                ("api", "claude-3.5-sonnet")
            ],
            "extraction": [
                ("api", "deepseek-v3"),
                ("browser", "deepseek"),
                ("api", "gpt-4o-mini")
            ],
            "general": [
                ("api", "llama-3.3-70b"),
                ("api", "gemma-4"),
                ("browser", "perplexity")
            ]
        }
        self.current_indices = {k: 0 for k in self.routing_map.keys()}

    def get_next_provider(self, intent: str):
        """Returns the next available provider for a given intent, rotating on failure."""
        if intent not in self.routing_map:
            intent = "general"
        
        providers = self.routing_map[intent]
        idx = self.current_indices[intent]
        
        provider_type, provider_name = providers[idx]
        
        # Advance index for next time (rotation)
        self.current_indices[intent] = (idx + 1) % len(providers)
        
        return {
            "type": provider_type,
            "name": provider_name
        }

    def report_failure(self, intent: str):
        """Increments the rotation index when a provider fails."""
        print(f"⚠️ Provider failure for {intent}. Rotating...")
        self.current_indices[intent] = (self.current_indices[intent] + 1) % len(self.routing_map[intent])

if __name__ == "__main__":
    # Quick test
    router = OmniChannelRouter()
    print(f"Initial: {router.get_next_provider('reasoning')}")
    print(f"Next (after rotation): {router.get_next_provider('reasoning')}")
