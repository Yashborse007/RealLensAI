import logging
import sys
import json
from datetime import datetime, timezone

class StructuredJsonFormatter(logging.Formatter):
    """
    Custom logging formatter outputting structured JSON lines for telemetry.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, "extra_data"):
            log_object["extra"] = record.extra_data
            
        return json.dumps(log_object)

def setup_logger(name: str = "RealLensAI-Service") -> logging.Logger:
    """
    Initialize and return a structured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredJsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()
