#!/usr/bin/env python3
"""
Dependency Injection Container - Service registry and resolution
Manages service lifecycles (singleton, transient, scoped)
"""

import inspect
import logging
from typing import Dict, Type, Callable, Optional, Any, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ServiceNotFoundError(Exception):
    """Raised when a service is not registered"""
    pass


class DIScope:
    """Represents a scope for scoped services"""
    
    def __init__(self, parent_container: 'DIContainer'):
        self.parent = parent_container
        self._instances: Dict[str, Any] = {}
    
    def get(self, name: str) -> Any:
        """Get service from scope or create it"""
        if name not in self._instances:
            self._instances[name] = self.parent._resolve_in_scope(name, self)
        return self._instances[name]
    
    def dispose(self) -> None:
        """Dispose all services in scope"""
        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.error(f"Error disposing instance: {e}")
        self._instances.clear()


class ServiceLifetime:
    """Service lifetime constants"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDefinition:
    """Defines how a service should be created"""
    
    def __init__(self, name: str, factory: Callable, lifetime: str,
                 dependencies: List[str] = None):
        self.name = name
        self.factory = factory
        self.lifetime = lifetime
        self.dependencies = dependencies or []
        self.instance = None  # For singletons


class DIContainer:
    """Dependency Injection Container"""
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._singletons: Dict[str, Any] = {}
        logger.info("DIContainer initialized")
    
    def register(self, name: str, factory: Callable, 
                lifetime: str = ServiceLifetime.SINGLETON,
                dependencies: Optional[List[str]] = None) -> None:
        """
        Register a service.
        
        Args:
            name: Service name/identifier
            factory: Callable that creates the service
            lifetime: ServiceLifetime constant (singleton, transient, scoped)
            dependencies: List of dependency names
        """
        definition = ServiceDefinition(name, factory, lifetime, dependencies)
        self._services[name] = definition
        logger.debug(f"Registered service: {name} ({lifetime})")
    
    def register_singleton(self, name: str, factory: Callable,
                          dependencies: Optional[List[str]] = None) -> None:
        """Register singleton service (created once, reused)"""
        self.register(name, factory, ServiceLifetime.SINGLETON, dependencies)
    
    def register_transient(self, name: str, factory: Callable,
                          dependencies: Optional[List[str]] = None) -> None:
        """Register transient service (created each time)"""
        self.register(name, factory, ServiceLifetime.TRANSIENT, dependencies)
    
    def register_scoped(self, name: str, factory: Callable,
                       dependencies: Optional[List[str]] = None) -> None:
        """Register scoped service (created per scope)"""
        self.register(name, factory, ServiceLifetime.SCOPED, dependencies)
    
    def get(self, name: str) -> Any:
        """
        Get a service instance.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            ServiceNotFoundError: If service not registered
        """
        if name not in self._services:
            raise ServiceNotFoundError(f"Service not registered: {name}")
        
        definition = self._services[name]
        
        if definition.lifetime == ServiceLifetime.SINGLETON:
            if name not in self._singletons:
                self._singletons[name] = self._create_instance(definition)
            return self._singletons[name]
        elif definition.lifetime == ServiceLifetime.TRANSIENT:
            return self._create_instance(definition)
        else:
            raise ValueError(f"Cannot get scoped service without scope: {name}")
    
    def create_scope(self) -> DIScope:
        """Create a new scope for scoped services"""
        return DIScope(self)
    
    def _resolve_in_scope(self, name: str, scope: DIScope) -> Any:
        """Resolve a service within a scope"""
        if name not in self._services:
            raise ServiceNotFoundError(f"Service not registered: {name}")
        
        definition = self._services[name]
        
        if definition.lifetime == ServiceLifetime.SINGLETON:
            return self.get(name)  # Get singleton from parent
        elif definition.lifetime == ServiceLifetime.SCOPED:
            return self._create_instance(definition)
        else:
            return self._create_instance(definition)
    
    def _create_instance(self, definition: ServiceDefinition) -> Any:
        """Create a service instance with dependency injection"""
        # Resolve dependencies
        kwargs = {}
        for dep_name in definition.dependencies:
            kwargs[dep_name] = self.get(dep_name)
        
        # Call factory
        try:
            return definition.factory(**kwargs)
        except Exception as e:
            logger.error(f"Error creating service {definition.name}: {e}")
            raise
    
    def resolve(self, target_class: Type) -> Any:
        """
        Auto-wire a class by inspecting its __init__ signature.
        Requires constructor parameters to be named same as registered services.
        
        Args:
            target_class: Class to instantiate
            
        Returns:
            Instance of target_class with dependencies injected
        """
        sig = inspect.signature(target_class.__init__)
        kwargs = {}
        
        for param_name in sig.parameters:
            if param_name == 'self':
                continue
            
            try:
                # Try to get service with parameter name
                kwargs[param_name] = self.get(param_name)
            except ServiceNotFoundError:
                logger.warning(f"Cannot resolve parameter: {param_name}")
        
        return target_class(**kwargs)
    
    def configure_from_dict(self, config: Dict[str, Any]) -> None:
        """
        Configure services from a dictionary.
        
        Format:
        {
            "service_name": {
                "factory": callable,
                "lifetime": "singleton",
                "dependencies": ["dep1", "dep2"]
            }
        }
        """
        for name, service_config in config.items():
            factory = service_config.get('factory')
            lifetime = service_config.get('lifetime', ServiceLifetime.SINGLETON)
            dependencies = service_config.get('dependencies', [])
            
            if factory:
                self.register(name, factory, lifetime, dependencies)
    
    def contains(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services
    
    def get_registered_services(self) -> List[str]:
        """Get list of registered service names"""
        return list(self._services.keys())
    
    def clear(self) -> None:
        """Clear all registered services and singletons"""
        self._services.clear()
        self._singletons.clear()
        logger.info("DIContainer cleared")


# Singleton instance
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get or create global container"""
    global _global_container
    if _global_container is None:
        _global_container = DIContainer()
    return _global_container


def set_container(container: DIContainer) -> None:
    """Set global container"""
    global _global_container
    _global_container = container
