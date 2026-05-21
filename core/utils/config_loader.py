"""
Configuration loader for AI agent settings
Supports YAML and JSON configuration files
"""
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Load and manage configuration files"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / 'configs'
        self._config_cache: Dict[str, Any] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        # Check cache
        cache_key = f"yaml:{filepath}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        with open(filepath, 'r') as f:
            config = yaml.safe_load(f)
        
        self._config_cache[cache_key] = config
        return config
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load a JSON configuration file"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        # Check cache
        cache_key = f"json:{filepath}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        self._config_cache[cache_key] = config
        return config
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        config = self.load_yaml('agent_config.yaml')
        return config.get('agents', {}).get(agent_name, {})
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration"""
        config = self.load_yaml('agent_config.yaml')
        return config.get('global', {})
    
    def reload(self):
        """Clear configuration cache"""
        self._config_cache.clear()


# Global instance for easy access
config_loader = ConfigLoader()

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Convenience function to get agent configuration"""
    return config_loader.get_agent_config(agent_name)

def get_global_config() -> Dict[str, Any]:
    """Convenience function to get global configuration"""
    return config_loader.get_global_config()