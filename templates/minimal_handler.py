"""
Minimal handler template - simplest possible working handler
"""

from typing import Dict, Any, Optional
from zephyr.handlers.base import HotHandler


class MinimalHandler(HotHandler):
    """A minimal working handler"""
    
    def __init__(self, node: 'ZephyrNode'):
        super().__init__(node)
        # Initialize any state here
        
    async def process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        msg_type = message.get('type')
        
        # Check if this is a message we handle
        if msg_type != 'YOUR_MESSAGE_TYPE':
            return None
            
        # Process the message
        payload = message.get('payload', {})
        
        # Return a response (or None if no response needed)
        return {
            'type': 'YOUR_RESPONSE_TYPE',
            'payload': {
                # Your response data
            }
        }