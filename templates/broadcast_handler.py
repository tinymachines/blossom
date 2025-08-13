"""
Broadcast handler template - sends periodic messages
"""

import asyncio
import time
from typing import Dict, Any, Optional
from zephyr.handlers.base import HotHandler
from zephyr.transport import TransportMessage


class BroadcastHandler(HotHandler):
    """Handler that broadcasts messages"""
    
    def __init__(self, node: 'ZephyrNode'):
        super().__init__(node)
        # State
        self.broadcast_interval = 30  # seconds
        self.last_broadcast = 0
        self._broadcast_task = None
        
    async def activate(self) -> None:
        """Start broadcasting"""
        await super().activate()
        # Start broadcast task
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        
    async def deactivate(self) -> None:
        """Stop broadcasting"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
        await super().deactivate()
        
    async def process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        msg_type = message.get('type')
        
        if msg_type == 'YOUR_MESSAGE_TYPE':
            # Handle message
            return {
                'type': 'YOUR_RESPONSE_TYPE',
                'payload': {}
            }
            
        return None
        
    async def _broadcast_loop(self):
        """Periodic broadcast task"""
        while self._active:
            try:
                await asyncio.sleep(self.broadcast_interval)
                
                # Create broadcast message
                msg = TransportMessage(
                    message_type='YOUR_BROADCAST_TYPE',
                    payload={
                        'timestamp': time.time(),
                        'data': 'YOUR_DATA'
                    },
                    src_addr=self.node.machine_id,
                    transport='handler'
                )
                
                # Broadcast
                await self.node.broadcast(msg)
                self.last_broadcast = time.time()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Broadcast error: {e}")