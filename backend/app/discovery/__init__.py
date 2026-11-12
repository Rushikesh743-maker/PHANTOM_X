try:
    from discovery.normalizer import EndpointNormalizer
    from discovery.scope_filter import ScopeFilter
    from discovery.parsers.openapi_parser import OpenApiParser
    from discovery.parsers.postman_parser import PostmanParser
    from discovery.parsers.har_parser import HarDiscoveryParser
except ImportError:
    from .normalizer import EndpointNormalizer
    from .scope_filter import ScopeFilter
    from .parsers.openapi_parser import OpenApiParser
    from .parsers.postman_parser import PostmanParser
    from .parsers.har_parser import HarDiscoveryParser

__all__ = [
    "EndpointNormalizer",
    "ScopeFilter",
    "OpenApiParser",
    "PostmanParser",
    "HarDiscoveryParser"
]
