try:
    from discovery.parsers.openapi_parser import OpenApiParser
    from discovery.parsers.postman_parser import PostmanParser
    from discovery.parsers.har_parser import HarDiscoveryParser
except ImportError:
    from .openapi_parser import OpenApiParser
    from .postman_parser import PostmanParser
    from .har_parser import HarDiscoveryParser

__all__ = ["OpenApiParser", "PostmanParser", "HarDiscoveryParser"]
