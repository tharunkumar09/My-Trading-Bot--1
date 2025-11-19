"""
Configuration Loader
Loads and validates configuration from YAML files and environment variables
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages configuration"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to config.yaml file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML and environment variables"""
        # Load environment variables
        env_path = self.config_path.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {env_path}")
        
        # Load YAML configuration
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config_str = f.read()
            
            # Replace environment variables in config
            config_str = os.path.expandvars(config_str)
            
            self.config = yaml.safe_load(config_str)
        
        logger.info(f"Loaded configuration from {self.config_path}")
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        required_sections = ['api', 'strategy', 'risk_management', 'universe']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate API credentials
        api_provider = self.config['api']['provider']
        if api_provider not in ['upstox', 'angelone']:
            raise ValueError(f"Invalid API provider: {api_provider}")
        
        api_config = self.config['api'][api_provider]
        if api_provider == 'upstox':
            if not api_config.get('api_key') or '${' in api_config.get('api_key', ''):
                logger.warning("Upstox API key not set in environment variables")
        elif api_provider == 'angelone':
            if not api_config.get('api_key') or '${' in api_config.get('api_key', ''):
                logger.warning("Angel One API key not set in environment variables")
        
        logger.info("Configuration validation passed")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path
        
        Args:
            key_path: Dot-separated path (e.g., 'api.provider')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        provider = self.get('api.provider')
        return {
            'provider': provider,
            **self.get(f'api.{provider}', {})
        }
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self.get('strategy', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return self.get('risk_management', {})
    
    def get_universe(self) -> Dict[str, Any]:
        """Get trading universe configuration"""
        return self.get('universe', {})
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """Get backtesting configuration"""
        return self.get('backtesting', {})
    
    def is_live_trading(self) -> bool:
        """Check if live trading is enabled"""
        return self.get('live_trading.enabled', False)
    
    def get_trading_mode(self) -> str:
        """Get trading mode (paper/live)"""
        return self.get('live_trading.mode', 'paper')


# Global config instance
_config_instance = None


def get_config(config_path: str = None) -> ConfigLoader:
    """
    Get global configuration instance
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance
