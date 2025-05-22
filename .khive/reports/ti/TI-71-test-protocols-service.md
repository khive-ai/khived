---
title: Test Implementation for Service Protocol
by: khive-implementer
created: 2025-05-14
updated: 2025-05-14
version: 1.0
doc_type: TI
output_subdir: ti
description: Detailed test implementation plan for the Service protocol
date: 2025-05-14
---

# Test Implementation Plan: Service Protocol

## 1. Overview

### 1.1 Component Under Test

The Service protocol (`src/khive/protocols/service.py`) is an abstract base
class that defines the contract for all service implementations in the khive
system. It requires concrete implementations to provide an async
`handle_request` method with a specific signature.

### 1.2 Test Approach

The test approach will be primarily unit testing, focusing on:

- Verifying the abstract nature of the Service class
- Testing that concrete implementations must implement the required methods
- Ensuring the method signature is enforced correctly
- Testing valid implementations function as expected

### 1.3 Key Testing Goals

- Verify Service is an abstract base class
- Verify handle_request is an abstract method
- Ensure concrete implementations must implement handle_request
- Verify handle_request signature is enforced (async with correct parameters)
- Achieve >80% test coverage for the module

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-asyncio  # For testing async methods
pytest-cov      # For coverage reporting
```

### 2.2 Mock Framework

```
unittest.mock   # For mocking dependencies if needed
```

## 3. Unit Tests

### 3.1 Test Suite: Service Protocol Structure

#### 3.1.1 Test Case: Service is an Abstract Base Class

**Purpose:** Verify that Service is an abstract base class and cannot be
instantiated directly.

**Test Implementation:**

```python
def test_service_is_abstract_base_class():
    """Test that Service is an abstract base class and cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class Service"):
        Service()
```

#### 3.1.2 Test Case: handle_request is an Abstract Method

**Purpose:** Verify that handle_request is marked as an abstract method.

**Test Implementation:**

```python
def test_handle_request_is_abstract_method():
    """Test that handle_request is an abstract method."""
    # Check if handle_request is in the __abstractmethods__ set
    assert "handle_request" in Service.__abstractmethods__
```

### 3.2 Test Suite: Service Implementation Validation

#### 3.2.1 Test Case: Valid Service Implementation

**Purpose:** Verify that a concrete class implementing handle_request can be
instantiated.

**Test Implementation:**

```python
class ValidService(Service):
    """Valid implementation of Service protocol."""

    async def handle_request(self, request, ctx=None):
        """Handle a request with the correct signature."""
        return {"status": "success", "data": request}

def test_valid_service_implementation():
    """Test that a valid Service implementation can be instantiated."""
    # Should not raise any exceptions
    service = ValidService()
    assert isinstance(service, Service)
```

#### 3.2.2 Test Case: Invalid Service Implementation

**Purpose:** Verify that a concrete class not implementing handle_request cannot
be instantiated.

**Test Implementation:**

```python
class InvalidService(Service):
    """Invalid implementation of Service protocol that doesn't implement handle_request."""
    pass

def test_invalid_service_implementation():
    """Test that an invalid Service implementation cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class InvalidService"):
        InvalidService()
```

### 3.3 Test Suite: Method Signature Enforcement

#### 3.3.1 Test Case: Non-Async handle_request

**Purpose:** Verify that handle_request must be an async method.

**Test Implementation:**

```python
class NonAsyncService(Service):
    """Invalid implementation with non-async handle_request."""

    def handle_request(self, request, ctx=None):
        """Non-async implementation of handle_request."""
        return {"status": "success", "data": request}

@pytest.mark.asyncio
async def test_non_async_handle_request():
    """Test that handle_request must be an async method."""
    service = NonAsyncService()

    # This should fail because handle_request is not async
    with pytest.raises(TypeError, match="object is not callable"):
        await service.handle_request({"query": "test"})
```

#### 3.3.2 Test Case: Missing Required Parameters

**Purpose:** Verify that handle_request must accept the required parameters.

**Test Implementation:**

```python
class MissingParamService(Service):
    """Invalid implementation with missing required parameters."""

    async def handle_request(self):
        """Implementation missing required parameters."""
        return {"status": "success"}

@pytest.mark.asyncio
async def test_missing_required_parameters():
    """Test that handle_request must accept the required parameters."""
    service = MissingParamService()

    # This should fail because handle_request doesn't accept the required parameters
    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        await service.handle_request({"query": "test"})
```

#### 3.3.3 Test Case: Extra Required Parameters

**Purpose:** Verify that handle_request with extra required parameters works
correctly.

**Test Implementation:**

```python
class ExtraParamService(Service):
    """Implementation with extra required parameters."""

    async def handle_request(self, request, ctx=None, extra_param=None):
        """Implementation with extra parameters."""
        return {"status": "success", "data": request, "extra": extra_param}

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
```

### 3.4 Test Suite: Functional Testing

#### 3.4.1 Test Case: Basic Functionality

**Purpose:** Verify that a valid Service implementation functions correctly.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_handle_request_functionality():
    """Test that handle_request functions correctly in a valid implementation."""
    service = ValidService()
    request = {"query": "test"}

    result = await service.handle_request(request)

    assert result["status"] == "success"
    assert result["data"] == request
```

#### 3.4.2 Test Case: Context Parameter

**Purpose:** Verify that the ctx parameter works correctly.

**Test Implementation:**

```python
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
```

## 4. Mock Implementation Details

```python
# Valid Service implementation
class ValidService(Service):
    """Valid implementation of Service protocol."""

    async def handle_request(self, request, ctx=None):
        """Handle a request with the correct signature."""
        return {"status": "success", "data": request}

# Invalid Service implementation (missing handle_request)
class InvalidService(Service):
    """Invalid implementation of Service protocol that doesn't implement handle_request."""
    pass

# Service with non-async handle_request
class NonAsyncService(Service):
    """Invalid implementation with non-async handle_request."""

    def handle_request(self, request, ctx=None):
        """Non-async implementation of handle_request."""
        return {"status": "success", "data": request}

# Service with missing required parameters
class MissingParamService(Service):
    """Invalid implementation with missing required parameters."""

    async def handle_request(self):
        """Implementation missing required parameters."""
        return {"status": "success"}

# Service with extra parameters
class ExtraParamService(Service):
    """Implementation with extra required parameters."""

    async def handle_request(self, request, ctx=None, extra_param=None):
        """Implementation with extra parameters."""
        return {"status": "success", "data": request, "extra": extra_param}

# Service that uses the context parameter
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
```

## 5. Test Coverage Targets

- **Line Coverage Target:** >80%
- **Branch Coverage Target:** >80%
- **Critical Aspects:** 100% coverage of abstract method definitions

## 6. Notes and Caveats

### 6.1 Known Limitations

- The tests focus on the protocol contract rather than specific implementations
- Some edge cases in method signature enforcement may be difficult to test
  comprehensively

### 6.2 Future Improvements

- Add more complex test cases for real-world service implementations
- Consider testing integration with other protocols like Invokable
