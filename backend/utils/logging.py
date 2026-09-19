import logging
import datetime
import asyncio
from typing import List, Dict, Any, Callable

# Memory buffer for logs (to show history on connection)
MAX_LOG_HISTORY = 1000
log_history: List[Dict[str, Any]] = []
log_callbacks: List[Callable[[Dict[str, Any]], None]] = []

class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "agent": getattr(record, "agent", "System"),
                "progress": getattr(record, "progress", None)
            }
            
            # Add to history
            log_history.append(log_entry)
            if len(log_history) > MAX_LOG_HISTORY:
                log_history.pop(0)
                
            # Trigger callbacks
            for callback in log_callbacks:
                try:
                    # Run callback
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(log_entry))
                    else:
                        callback(log_entry)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)

# Register custom handler
def setup_websocket_logging():
    handler = WebSocketLogHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    # Check if handler already registered
    already_exists = False
    for h in root_logger.handlers:
        if isinstance(h, WebSocketLogHandler):
            already_exists = True
            break
    if not already_exists:
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    return handler

# Helper to register WebSocket callbacks
def register_log_callback(callback: Callable[[Dict[str, Any]], None]):
    if callback not in log_callbacks:
        log_callbacks.append(callback)

def unregister_log_callback(callback: Callable[[Dict[str, Any]], None]):
    if callback in log_callbacks:
        log_callbacks.remove(callback)

# Context logger helper
class AgentLoggerAdapter(logging.LoggerAdapter):
    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            extra = self.extra or {}
            if "agent" in kwargs:
                extra["agent"] = kwargs.pop("agent")
            if "progress" in kwargs:
                extra["progress"] = kwargs.pop("progress")
            kwargs["extra"] = extra
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, msg, args, **kwargs)

def get_agent_logger(agent_name: str) -> AgentLoggerAdapter:
    logger = logging.getLogger(f"trade_intel.agents.{agent_name.lower().replace(' ', '_')}")
    return AgentLoggerAdapter(logger, {"agent": agent_name, "progress": 0.0})
