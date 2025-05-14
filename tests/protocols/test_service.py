"""
Tests for khive.protocols.service module.
"""

import inspect
import pytest

from abc import abstractmethod

from khive.protocols.service import Service


# --- Mock classes for testing ---
class ValidService(Service):
    """Valid implementation of Service protocol."""
    
    async def handle_request(self, request, ctx=None):
        """Handle a request with the correct signature."""
        return {"status": "success", "data": request}


class InvalidService(Service):
    """Invalid implementation of Service protocol that doesn't implement handle_request."""
    pass


class NonAsyncService(Service):
    """Invalid implementation with non-async handle_request."""
    
    def handle_request(self, request, ctx=None):
        """Non-async implementation of handle_request."""
        return {"status": "success", "data": request}


class MissingParamService(Service):
    """Invalid implementation with missing required parameters."""
    
    async def handle_request(self):
        """Implementation missing required parameters."""
        return {"status": "success"}


class ExtraParamService(Service):
    """Implementation with extra required parameters."""
    
    async def handle_request(self, request, ctx=None, extra_param=None):
        """Implementation with extra parameters."""
        return {"status": "success", "data": request, "extra": extra_param}


class ContextAwareService(Service):
    """Service implementation that uses the context parameter."""
    
    async def handle_request(self, request, ctx=None):
        """Handle a request using the context parameter."""
        ctx = ctx or {}
        return {
            "status": "success",
            "data": request,
            "context": ctx
        }


# --- Tests for Service protocol structure ---
def test_service_has_abstractmethod_decorator():
    """Test that handle_request is decorated with @abstractmethod."""
    # Get the handle_request method from the Service class
    method = getattr(Service, "handle_request")
    
    # Check if the method has the __isabstractmethod__ attribute set to True
    assert getattr(method, "__isabstractmethod__", False) is True


def test_handle_request_is_defined():
    """Test that handle_request is defined in the Service class."""
    assert hasattr(Service, "handle_request")


# --- Tests for Service implementation validation ---
def test_valid_service_implementation():
    """Test that a valid Service implementation can be instantiated."""
    # Should not raise any exceptions
    service = ValidService()
    assert isinstance(service, Service)


def test_invalid_service_implementation():
    """Test that an invalid Service implementation can still be instantiated.
    
    Note: Since Service is not a true ABC (doesn't inherit from abc.ABC),
    subclasses that don't implement handle_request can still be instantiated.
    The abstract method is inherited from the parent class.
    """
    # This should not raise an exception
    service = InvalidService()
    assert isinstance(service, Service)
    
    # The handle_request method is inherited from Service
    assert hasattr(service, "handle_request")


# --- Tests for method signature enforcement ---
def test_handle_request_is_async():
    """Test that handle_request is defined as an async method."""
    # Get the handle_request method from the Service class
    method = getattr(Service, "handle_request")
    
    # Check if the method is a coroutine function
    assert inspect.iscoroutinefunction(method) is True, "Abstract method should be a coroutine function"
    
    # Check the valid implementation
    valid_method = getattr(ValidService, "handle_request")
    assert inspect.iscoroutinefunction(valid_method) is True, "Implementation should be a coroutine function"


@pytest.mark.asyncio
async def test_non_async_handle_request():
    """Test that a non-async handle_request implementation can't be awaited."""
    service = NonAsyncService()
    
    # This should fail because handle_request is not async
    with pytest.raises(TypeError):
        await service.handle_request({"query": "test"})


@pytest.mark.asyncio
async def test_missing_required_parameters():
    """Test that handle_request must accept the required parameters."""
    service = MissingParamService()
    
    # This should fail because handle_request doesn't accept the required parameters
    with pytest.raises(TypeError, match="takes 1 positional argument but 2 were given"):
        await service.handle_request({"query": "test"})


@pytest.mark.asyncio
async def test_extra_parameters():
    """Test that handle_request can have extra parameters with defaults."""
    service = ExtraParamService()
    
    # This should work because the extra parameter has a default value
    result = await service.handle_request({"query": "test"})
    assert result["status"] == "success"
    assert result["data"] == {"query": "test"}
    assert result["extra"] is None
    
    # This should also work when providing the extra parameter
    result = await service.handle_request({"query": "test"}, None, "extra_value")
    assert result["extra"] == "extra_value"


# --- Tests for functional behavior ---
@pytest.mark.asyncio
async def test_handle_request_functionality():
    """Test that handle_request functions correctly in a valid implementation."""
    service = ValidService()
    request = {"query": "test"}
    
    result = await service.handle_request(request)
    
    assert result["status"] == "success"
    assert result["data"] == request


@pytest.mark.asyncio
async def test_context_parameter():
    """Test that the ctx parameter works correctly."""
    service = ContextAwareService()
    request = {"query": "test"}
    ctx = {"user_id": "123"}
    
    # Test with context provided
    result = await service.handle_request(request, ctx)
    assert result["context"] == ctx
    
    # Test with default context
    result = await service.handle_request(request)
    assert result["context"] == {}


@pytest.mark.asyncio
async def test_handle_request_parameter_types():
    """Test that handle_request accepts different parameter types."""
    service = ValidService()
    
    # Test with dict request
    result = await service.handle_request({"query": "test"})
    assert result["data"] == {"query": "test"}
    
    # Test with string request
    result = await service.handle_request("test string")
    assert result["data"] == "test string"
    
    # Test with None request
    result = await service.handle_request(None)
    assert result["data"] is None


@pytest.mark.asyncio
async def test_inherited_abstract_method_behavior():
    """Test the behavior of the inherited abstract method.
    
    Note: In this implementation, the @abstractmethod decorator doesn't cause
    a NotImplementedError to be raised when the method is called. Instead,
    it simply returns the value from the pass statement (None).
    """
    service = InvalidService()
    
    # Calling the inherited abstract method should return None
    result = await service.handle_request({"query": "test"})
    assert result is None