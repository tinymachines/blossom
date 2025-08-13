"""
Stateful handler template - maintains state between messages
"""

import asyncio
from typing import Dict, Any, Optional
from zephyr.handlers.base import HotHandler


class StatefulHandler(HotHandler):
    """Handler that maintains state"""
    
    def __init__(self, node: 'ZephyrNode'):
        super().__init__(node)
        # Initialize state variables
        self.counter = 0
        self.data = {}
        
    async def activate(self) -> None:
        """Called when handler is activated"""
        await super().activate()
        # Start any background tasks here
        
    async def process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        msg_type = message.get('type')
        
        # Update state
        self.counter += 1
        
        # Handle different message types
        if msg_type == 'YOUR_MESSAGE_TYPE':
            # Process and update state
            payload = message.get('payload', {})
            
            # Store data
            self.data[msg_type] = payload
            
            # Return response
            return {
                'type': 'YOUR_RESPONSE_TYPE',
                'payload': {
                    'count': self.counter,
                    'data': self.data
                }
            }
            
        return None