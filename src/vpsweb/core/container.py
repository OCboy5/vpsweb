"""
Dependency Injection Container for Phase 3 refactoring.

This module provides a lightweight dependency injection container to support
the Phase 3 refactoring efforts, enabling better testability and modularity.
"""

from typing import Dict, Type, TypeVar, Any, Optional, List, Callable
from abc import ABC, abstractmethod
import inspect
from enum import Enum

# Generic type variable for dependency injection
T = TypeVar('T')


class LifetimeScope(Enum):
    """Dependency lifetime scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class DIContainer:
    """
    Simple dependency injection container for Phase 3 refactoring.

    Supports registration and resolution of dependencies with different
    lifetime scopes and factory functions.
    """

    def __init__(self):
        self._registrations: Dict[Type, Dict[str, Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._current_scope: Optional[str] = None

    def register(
        self,
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        *,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
        name: Optional[str] = None
    ) -> None:
        """
        Register a dependency in the container.

        Args:
            interface: The interface or base type
            implementation: The concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance (only for SINGLETON)
            lifetime: Lifetime scope for the dependency
            name: Optional name for named registrations
        """
        key = name if name else interface

        if key in self._registrations:
            raise ValueError(f"Dependency {key} is already registered")

        if sum(bool(x) for x in [implementation, factory, instance]) != 1:
            raise ValueError("Exactly one of implementation, factory, or instance must be provided")

        if instance and lifetime != LifetimeScope.SINGLETON:
            raise ValueError("Instance can only be registered with SINGLETON lifetime")

        self._registrations[key] = {
            'interface': interface,
            'implementation': implementation,
            'factory': factory,
            'instance': instance,
            'lifetime': lifetime
        }

    def register_singleton(self, interface: Type[T], implementation: Type[T], name: Optional[str] = None) -> None:
        """Register a singleton dependency."""
        self.register(interface, implementation=implementation, lifetime=LifetimeScope.SINGLETON, name=name)

    def register_transient(self, interface: Type[T], implementation: Type[T], name: Optional[str] = None) -> None:
        """Register a transient dependency."""
        self.register(interface, implementation=implementation, lifetime=LifetimeScope.TRANSIENT, name=name)

    def register_scoped(self, interface: Type[T], implementation: Type[T], name: Optional[str] = None) -> None:
        """Register a scoped dependency."""
        self.register(interface, implementation=implementation, lifetime=LifetimeScope.SCOPED, name=name)

    def register_factory(self, interface: Type[T], factory: Callable[[], T], name: Optional[str] = None) -> None:
        """Register a factory function."""
        self.register(interface, factory=factory, name=name)

    def register_instance(self, interface: Type[T], instance: T, name: Optional[str] = None) -> None:
        """Register a pre-created instance."""

        self.register(interface, instance=instance, lifetime=LifetimeScope.SINGLETON, name=name)

    def resolve(self, interface: Type[T], name: Optional[str] = None) -> T:
        """
        Resolve a dependency from the container.

        Args:
            interface: The interface or base type to resolve
            name: Optional name for named registrations

        Returns:
            An instance of the requested type
        """
        key = name if name else interface



        if key not in self._registrations:
            raise ValueError(f"Dependency {key} is not registered")

        registration = self._registrations[key]
        lifetime = registration['lifetime']

        # Check singletons first
        if lifetime == LifetimeScope.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]

            instance = self._create_instance(registration)
            self._singletons[interface] = instance
            return instance

        # Check scoped instances
        elif lifetime == LifetimeScope.SCOPED:
            if self._current_scope and self._current_scope in self._scoped_instances:
                if interface in self._scoped_instances[self._current_scope]:
                    return self._scoped_instances[self._current_scope][interface]

            instance = self._create_instance(registration)

            if self._current_scope:
                if self._current_scope not in self._scoped_instances:
                    self._scoped_instances[self._current_scope] = {}
                self._scoped_instances[self._current_scope][interface] = instance

            return instance

        # Transient - always create new instance
        else:
            return self._create_instance(registration)

    def _create_instance(self, registration: Dict[str, Any]) -> Any:
        """Create an instance based on registration configuration."""
        if registration['instance']:
            return registration['instance']

        elif registration['factory']:
            return registration['factory']()

        elif registration['implementation']:
            implementation = registration['implementation']

            # Check if implementation requires constructor injection
            constructor_params = self._get_constructor_dependencies(implementation)

            if constructor_params:
                dependencies = {}
                for param_name, param_type in constructor_params.items():
                    dependencies[param_name] = self.resolve(param_type)

                return implementation(**dependencies)
            else:
                return implementation()

        else:
            raise ValueError(f"No valid creation strategy for {registration['interface']}")

    def _get_constructor_dependencies(self, cls: Type) -> Dict[str, Type]:
        """Analyze constructor to identify dependencies for injection."""
        constructor = cls.__init__
        signature = inspect.signature(constructor)
        dependencies = {}

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            # Only inject dependencies for parameters without defaults
            # that have type annotations
            if (param.annotation != inspect.Parameter.empty and
                param.default == inspect.Parameter.empty):
                dependencies[param_name] = param.annotation

        return dependencies

    def create_scope(self, scope_name: str) -> 'DIScope':
        """Create a new dependency scope."""
        return DIScope(self, scope_name)

    def begin_scope(self, scope_name: str) -> None:
        """Begin a new scope context."""
        self._current_scope = scope_name
        if scope_name not in self._scoped_instances:
            self._scoped_instances[scope_name] = {}

    def end_scope(self) -> None:
        """End the current scope context and cleanup scoped instances."""
        if self._current_scope and self._current_scope in self._scoped_instances:
            scope_instances = self._scoped_instances[self._current_scope]

            # Cleanup scoped instances
            for instance in scope_instances.values():
                if hasattr(instance, 'cleanup'):
                    try:
                        cleanup_method = getattr(instance, 'cleanup')
                        if callable(cleanup_method):
                            cleanup_method()
                    except Exception:
                        # Ignore cleanup errors
                        pass

            del self._scoped_instances[self._current_scope]

        self._current_scope = None

    def is_registered(self, interface: Type, name: Optional[str] = None) -> bool:
        """Check if a dependency is registered."""
        key = name if name else interface
        return key in self._registrations

    def get_registrations(self) -> List[Type]:
        """Get all registered interfaces."""
        return list(self._registrations.keys())

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._registrations.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        self._current_scope = None

    def cleanup(self) -> None:
        """Cleanup all resources and instances."""
        # Cleanup singletons
        for instance in self._singletons.values():
            if hasattr(instance, 'cleanup'):
                try:
                    cleanup_method = getattr(instance, 'cleanup')
                    if callable(cleanup_method):
                        cleanup_method()
                except Exception:
                    # Ignore cleanup errors
                    pass

        # Cleanup all scopes
        for scope_name in list(self._scoped_instances.keys()):
            self.end_scope()

        self.clear()


class DIScope:
    """Context manager for dependency injection scopes."""

    def __init__(self, container: DIContainer, scope_name: str):
        self.container = container
        self.scope_name = scope_name

    def __enter__(self) -> DIContainer:
        self.container.begin_scope(self.scope_name)
        return self.container

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container.end_scope()


# Service locator for global access (use sparingly)
class ServiceLocator:
    """
    Global service locator for dependency injection.

    Provides application-wide access to the DI container.
    Should be used sparingly in favor of constructor injection.
    """

    _instance: Optional['ServiceLocator'] = None
    _container: Optional[DIContainer] = None

    def __new__(cls) -> 'ServiceLocator':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_container(self, container: DIContainer) -> None:
        """Set the global DI container."""
        self._container = container

    def get_container(self) -> DIContainer:
        """Get the global DI container."""
        if self._container is None:
            raise ValueError("DI container not initialized")
        return self._container

    def resolve(self, interface: Type[T], name: Optional[str] = None) -> T:
        """Resolve a dependency from the global container."""
        return self.get_container().resolve(interface, name)

    def clear(self) -> None:
        """Clear the global container."""
        self._container = None


# Decorator for constructor injection support
def injectable(cls: Type[T]) -> Type[T]:
    """
    Decorator to mark a class as injectable.

    This decorator doesn't modify the class but serves as a marker
    for documentation and potential future enhancements.
    """
    return cls


# Utility functions for common DI patterns
def auto_register(container: DIContainer, module: Any, lifetime: LifetimeScope = LifetimeScope.TRANSIENT) -> None:
    """
    Automatically register all classes in a module that implement interfaces.

    Args:
        container: DI container to register in
        module: Module object to scan
        lifetime: Default lifetime for registrations
    """
    for name in dir(module):
        obj = getattr(module, name)

        if inspect.isclass(obj) and hasattr(obj, '__bases__'):
            # Look for classes that inherit from ABC or have 'Interface' in the name
            for base in obj.__bases__:
                if (abc := base) != ABC and hasattr(abc, '__abstractmethods__') and abc.__abstractmethods__:
                    # This class implements an abstract base class
                    container.register(base, obj, lifetime=lifetime)
                    break

_container_instance = DIContainer()

def get_container() -> DIContainer:
    return _container_instance