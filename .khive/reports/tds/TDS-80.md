---
title: "Technical Design Specification: Layered Resource Control Architecture (Issue #80)"
by: "@khive-architect"
created: "2025-05-22"
updated: "2025-05-22"
version: "1.0"
doc_type: "TDS"
identifier: "80"
output_subdir: "tds"
description: "Defines a layered resource control architecture for khive, leveraging lionfuncs components as per Issue #80 and TDS-100."
---

# Guidance

**Purpose** Lay out an **implementation-ready** blueprint for `khive`'s resource
control architecture, detailing how it leverages the `lionfuncs` package for
external API interactions, rate limiting, and concurrency.

**When to Use**

- After Research and initial architectural proposals (Issue #80, Issue #100,
  TDS-100.md).
- Before the Implementation Plan for these architectural changes.

**Best Practices**

- Keep the design as **complete** as possible.
- Emphasize how `lionfuncs` components map to the architectural layers.
- Use diagrams (Mermaid) for clarity.

---

# Technical Design Specification: Layered Resource Control Architecture (Issue #80)

## 1. Overview

### 1.1 Purpose

This document details the technical design for a layered resource control
architecture within `khive`. This architecture aims to provide clear separation
of concerns for handling external API interactions, focusing on rate limiting,
concurrent execution, and resource management. It heavily leverages the
`lionfuncs` package, as outlined in Issue #100 and `TDS-100.md`, to provide the
underlying infrastructure for these concerns.

### 1.2 Scope

**In Scope:**

- Definition of the architectural layers for resource control in `khive`.
- Specification of which `lionfuncs` components (e.g., `NetworkExecutor`,
  `AsyncAPIClient`, `BoundedQueue`) are used at each layer.
- Definition of `khive`-specific wrapper classes or service layers that utilize
  `lionfuncs`.
- Clear definition of component responsibilities and their interfaces (Python
  Protocols).
- Interaction diagrams illustrating request flows.
- Description of resource lifecycle management within `khive`.

**Out of Scope:**

- The actual implementation of the code changes.
- Detailed design of `lionfuncs` itself (assumed to be a provided, functional
  library).
- Changes to `khive`'s core business logic unrelated to resource control and
  external API communication.

### 1.3 Background

This design is based on the architectural proposal in **Issue #80:
"Architecture: Define a layered resource control architecture with clear
component responsibilities"** and the strategic direction to use `lionfuncs` for
network and concurrency primitives as detailed in **Issue #100: "Architectural
Refactor: Align Clients, Executor, Queue with New Design Philosophy"** and
**`TDS-100.md`**.

The proposed layers from Issue #80 are:

1. User-Facing API (e.g., `khive` CLI)
2. Service Layer (`khive` specific, e.g., `InfoService`)
3. Rate Limited Executor
4. Resource Client

This TDS will adapt this layered model to incorporate `lionfuncs` components.

### 1.4 Design Goals

- **Clear Layering:** Establish well-defined layers for resource control.
- **`lionfuncs` Integration:** Effectively utilize `lionfuncs` for rate
  limiting, execution, and client interactions.
- **Decoupling:** Decouple `khive` application logic from the complexities of
  direct external API management.
- **Maintainability:** Improve code organization and maintainability.
- **Testability:** Ensure components are easily testable, with clear mocking
  points for `lionfuncs`.
- **Lifecycle Management:** Define robust lifecycle management for all
  components.

### 1.5 Key Constraints

- All external API calls from `khive` must be routed through this new
  architecture, utilizing `lionfuncs`.
- Existing `khive` user-facing interfaces (CLI) should remain largely unchanged.
- The design must align with the principles outlined in Issue #80 and
  `TDS-100.md`.

## 2. Architecture

### 2.1 Component Diagram

The architecture integrates `khive`'s service layer with `lionfuncs` for
resource control and external communication.

```mermaid
graph TD
    subgraph khive Application
        UserCLI["User-Facing API (khive CLI)"]
        KhiveServiceLayer["khive Service Layer (e.g., InfoService, Future Services)"]
    end

    subgraph Resource Control Layer (Powered by lionfuncs)
        direction LR
        LionfuncsExecutor["lionfuncs.network.Executor (Handles Rate Limiting, Concurrency, Execution)"]
        LionfuncsClient["lionfuncs.network.AsyncAPIClient / Endpoint Interactions (via Executor or directly if appropriate)"]
        LionfuncsConcurrency["lionfuncs.concurrency (e.g., BoundedQueue, Semaphores - used by Executor or Service Layer)"]
    end

    subgraph External Services
        direction LR
        ExtAPI1["External API 1 (e.g., Exa)"]
        ExtAPI2["External API 2 (e.g., Perplexity)"]
        ExtAPI_N["... Other APIs"]
    end

    UserCLI --> KhiveServiceLayer
    KhiveServiceLayer --> LionfuncsExecutor
    %% KhiveServiceLayer might also directly use LionfuncsClient if Executor is purely for rate-limited execution of arbitrary functions
    %% KhiveServiceLayer -.-> LionfuncsClient

    LionfuncsExecutor --> LionfuncsClient %% Executor uses Client or configured Endpoints
    LionfuncsClient --> ExtAPI1
    LionfuncsClient --> ExtAPI2
    LionfuncsClient --> ExtAPI_N

    KhiveServiceLayer -.-> LionfuncsConcurrency %% For managing service-level concurrency if needed
    LionfuncsExecutor -.-> LionfuncsConcurrency %% Executor internally uses concurrency primitives
```

**Layer Mapping (Issue #80 to `lionfuncs`):**

- **User-Facing API:** Remains `khive` CLI and potentially other future
  interfaces.
- **Service Layer:** `khive`-specific services (e.g.,
  [`InfoService`](src/khive/services/info/info_service.py:0)). This layer is
  responsible for:
  - Understanding `khive`'s application logic.
  - Preparing requests and interpreting responses.
  - Orchestrating calls to the `lionfuncs`-powered layers.
- **Rate Limited Executor:** Primarily fulfilled by
  `lionfuncs.network.Executor`, which is expected to handle rate limiting, retry
  logic, and concurrent execution of tasks (API calls). (Ref: `TDS-100.md`,
  conceptual `lionfuncs` Network Executor Usage Guide)
- **Resource Client:** Interactions with external APIs will be managed via
  `lionfuncs.network.AsyncAPIClient` or through endpoint configurations passed
  to `lionfuncs.network.Executor`. (Ref: `TDS-100.md`, conceptual `lionfuncs`
  Network Client Guide)

### 2.2 Dependencies

- **`khive` on `lionfuncs`:** `khive`'s service layer will directly depend on
  `lionfuncs` interfaces.
- **`lionfuncs`:** Provides `NetworkExecutor`, `AsyncAPIClient`,
  `EndpointConfig`, `RequestModel`, `ResponseModel`, and concurrency utilities
  (e.g., `BoundedQueue`). (Ref: `TDS-100.md`)

## 3. Component Responsibilities & Interfaces

### 3.1 `khive` Service Layer (e.g., `InfoService`)

- **Responsibilities:**
  - Translate `khive` application requests into parameters suitable for
    `lionfuncs`.
  - Invoke `lionfuncs.network.Executor` (or `AsyncAPIClient` via Executor) with
    appropriate `EndpointConfig` and request data.
  - Handle responses and errors from `lionfuncs`, mapping them to `khive` domain
    models and exceptions.
  - Manage application-specific logic before and after external calls.
  - Potentially manage higher-level concurrency or batching using
    `lionfuncs.concurrency` if needed beyond what the `Executor` provides for
    individual calls.
- **Interface (Conceptual):**
  ```python
  from typing import Protocol, Any, Dict
  from lionfuncs.network import NetworkExecutor # Assuming import
  # from lionfuncs.models import ResponseModel # Assuming import

  class KhiveResourceService(Protocol):
      def __init__(self, executor: NetworkExecutor, #... other dependencies
                   ): ...

      async def make_external_call(self, service_identifier: str, request_data: Dict[str, Any]) -> Any: # Actually lionfuncs.ResponseModel or mapped khive model
          """
          Makes a call to an external service identified by service_identifier.
          Uses the lionfuncs.network.Executor for the actual call.
          """
          ...
  ```

### 3.2 `lionfuncs.network.Executor`

- **Responsibilities (as per `TDS-100.md` and conceptual docs):**
  - Execute tasks (functions, API calls via configured endpoints) concurrently.
  - Enforce rate limits per endpoint or globally.
  - Manage retry logic for failed attempts.
  - Utilize `lionfuncs.concurrency` primitives (e.g., `BoundedQueue`,
    semaphores) for managing concurrent operations.
  - Handle lifecycle of underlying resources if it manages clients directly
    (e.g., session pooling if `AsyncAPIClient` instances are created and managed
    per endpoint by the executor).
- **Interface (Conceptual, from `TDS-100.md` and Issue #80):**
  ```python
  from typing import Protocol, Any, Awaitable, Callable
  # from lionfuncs.network import EndpointConfig, RequestModel, ResponseModel # Assuming imports

  class ILionfuncsNetworkExecutor(Protocol):
      async def execute(
          self,
          # Option 1: Pass a pre-configured client/callable
          # func: Callable[..., Awaitable[ResponseModel]], *args, **kwargs
          # Option 2: Pass endpoint config and request data (more likely for this layer)
          endpoint_config: Any, # lionfuncs.network.EndpointConfig
          request_data: Any, # lionfuncs.models.RequestModel
          **kwargs # For additional execution options
      ) -> Any: # lionfuncs.models.ResponseModel
          ...

      async def shutdown(self, timeout: float = None) -> None:
          ...

      # May also include methods for direct function execution if it's a general executor
      # async def submit(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T: ...
  ```
  _Note: The exact signature will depend on `lionfuncs`'s actual API.
  `TDS-100.md` suggests `execute(endpoint_config, request_data)`._

### 3.3 `lionfuncs.network.AsyncAPIClient` / Endpoint Interaction

- **Responsibilities (as per `TDS-100.md` and conceptual docs):**
  - Direct interaction with a specific external API endpoint.
  - Handling HTTP request/response serialization/deserialization.
  - Managing connection pooling for its specific endpoint (if it's a long-lived
    client).
  - Authentication specific to an endpoint.
- **Interface (Conceptual):**
  ```python
  from typing import Protocol, Any
  # from lionfuncs.models import RequestModel, ResponseModel # Assuming imports

  class ILionfuncsAsyncAPIClient(Protocol):
      async def request(self, request_data: Any # lionfuncs.models.RequestModel
                        ) -> Any: # lionfuncs.models.ResponseModel
          ...

      async def close(self) -> None: ...
      async def __aenter__(self) -> 'ILionfuncsAsyncAPIClient': ...
      async def __aexit__(self, *args) -> None: ...
  ```
  _Note: `khive` services might not interact with `AsyncAPIClient` directly if
  the `NetworkExecutor` abstracts this away by taking `EndpointConfig`._

### 3.4 `lionfuncs.concurrency` (e.g., `BoundedQueue`)

- **Responsibilities (as per `TDS-100.md` and conceptual docs):**
  - Provide concurrency primitives like bounded queues, semaphores, etc.
- **Interface:** Standard interfaces for these primitives (e.g., `put`, `get`
  for a queue). _`khive` services might use these directly for managing batches
  of tasks to submit to the `NetworkExecutor`, or the `NetworkExecutor` might
  use them internally._

## 4. Interaction Diagrams

### 4.1 Request Flow: `khive info search`

```mermaid
sequenceDiagram
    participant User
    participant khive_CLI
    participant InfoService_khive
    participant Lionfuncs_NetworkExecutor
    participant Lionfuncs_AsyncAPIClient_or_EndpointLogic
    participant External_API (e.g., Exa)

    User->>khive_CLI: khive info search --provider exa --query "..."
    khive_CLI->>InfoService_khive: search(provider="exa", query="...")
    InfoService_khive->>InfoService_khive: Prepare lionfuncs.EndpointConfig for Exa
    InfoService_khive->>InfoService_khive: Prepare lionfuncs.RequestModel for Exa query
    InfoService_khive->>Lionfuncs_NetworkExecutor: execute(exa_endpoint_config, exa_request_model)
    Lionfuncs_NetworkExecutor->>Lionfuncs_NetworkExecutor: Acquire rate limit token
    Lionfuncs_NetworkExecutor->>Lionfuncs_AsyncAPIClient_or_EndpointLogic: Make HTTP Call(request_model)
    Lionfuncs_AsyncAPIClient_or_EndpointLogic->>External_API: HTTP POST /search
    External_API-->>Lionfuncs_AsyncAPIClient_or_EndpointLogic: HTTP Response
    Lionfuncs_AsyncAPIClient_or_EndpointLogic-->>Lionfuncs_NetworkExecutor: lionfuncs.ResponseModel
    Lionfuncs_NetworkExecutor-->>InfoService_khive: lionfuncs.ResponseModel
    InfoService_khive->>InfoService_khive: Process response, map to khive domain model
    InfoService_khive-->>khive_CLI: Formatted results / khive model
    khive_CLI-->>User: Display results
```

## 5. Lifecycle Management

### 5.1 Initialization

- **`lionfuncs.network.Executor`:**
  - An instance of `NetworkExecutor` should be created globally or per
    application scope within `khive` (e.g., when the `khive` application starts
    or on first use by a service).
  - Configuration for the executor (e.g., global concurrency limits, default
    rate limits if not per-endpoint) would be passed during its instantiation.
  - This executor instance will be injected into `khive` services (like
    `InfoService`).
- **`khive` Services (e.g., `InfoService`):**
  - Instantiated with a reference to the shared `lionfuncs.network.Executor`.
  - Load their specific configurations (e.g., how to prepare `EndpointConfig`
    for various external APIs).

### 5.2 Startup

- The `lionfuncs.network.Executor` might have an explicit startup phase if it
  needs to initialize internal resources (e.g., worker pools, internal queues).
  This should be called during `khive`'s application startup.
- If `lionfuncs.network.AsyncAPIClient` instances are managed by `khive`
  services (less likely if Executor handles endpoints), they would be
  initialized, potentially using async context managers.

### 5.3 Execution

- `khive` services prepare `EndpointConfig` and `RequestModel` objects.
- These are passed to the `lionfuncs.network.Executor.execute()` method.
- The Executor manages the call lifecycle, including rate limiting, retries, and
  actual dispatch to the external API (likely via an internal `AsyncAPIClient`
  or similar mechanism).

### 5.4 Shutdown

- **`lionfuncs.network.Executor`:**
  - Must provide a graceful shutdown mechanism (e.g.,
    `await executor.shutdown(timeout=...)`).
  - This should allow pending tasks to complete up to a certain timeout and
    clean up all internal resources (threads, connections, queues).
  - This shutdown method will be called during `khive`'s application shutdown
    sequence.
- **`khive` Services:**
  - If they manage any `lionfuncs` resources directly (e.g., client instances
    not managed by the Executor), they must ensure these are closed during
    shutdown, preferably using `async with` for individual clients if used
    ad-hoc, or an explicit close if long-lived and managed by the service.

### 5.5 Resource Cleanup

- `lionfuncs` components are responsible for cleaning up their internal
  resources (e.g., HTTP client sessions within `AsyncAPIClient` or the
  `NetworkExecutor`).
- `khive` is responsible for ensuring that `lionfuncs` components it manages
  (like the global `NetworkExecutor`) are properly shut down.
- Use of `async with` for any `lionfuncs` clients or resources that support the
  context manager protocol is highly recommended within `khive` service methods
  if they are created on-the-fly (though a central Executor is preferred).

## 6. Error Handling

- `lionfuncs` is expected to raise specific exceptions for network issues, API
  errors, timeouts, rate limit exceeded errors, etc. (Ref: `TDS-100.md`, Section
  5.2).
- `khive` Service Layer will catch these `lionfuncs` exceptions and:
  - Map them to appropriate `khive`-specific exceptions (e.g., from
    [`src/khive/clients/errors.py`](src/khive/clients/errors.py:0), which may be
    adapted).
  - Log them with relevant context.
  - Propagate them in a way that the `khive` CLI can present informative
    messages to the user.

## 7. Security Considerations

- API Key Management: `khive` services will continue to manage API keys, passing
  them to `lionfuncs` components (e.g., within `EndpointConfig`) as needed.
  `lionfuncs` should not store these keys beyond the scope of a request or its
  client configuration.
- `lionfuncs` is assumed to use HTTPS for all communications.

## 8. Testing Strategy

- **Unit Tests for `khive` Services:**
  - Mock the `lionfuncs.network.Executor` interface.
  - Verify that `khive` services correctly prepare `EndpointConfig` and
    `RequestModel` for `lionfuncs`.
  - Verify correct handling of responses and exceptions from the mocked
    `Executor`.
- **Integration Tests:**
  - Test the `khive` Service Layer interacting with a real (or well-mocked at
    its boundary) `lionfuncs.network.Executor`.
  - These tests might involve `lionfuncs` making calls to mock external API
    servers or, in controlled environments, to actual sandboxed external APIs.
  - Focus on the interaction between `khive` services and the `lionfuncs` layer.

## 9. Risks and Mitigations

- **Risk:** `lionfuncs.network.Executor` does not provide sufficient granularity
  for rate limiting or concurrency control as envisioned by Issue #80.
  - **Mitigation:** Early validation of `lionfuncs.network.Executor`
    capabilities against Issue #80 requirements. If gaps exist, `khive` Service
    Layer might need to implement additional controls using
    `lionfuncs.concurrency` primitives before submitting tasks to the
    `Executor`, or this needs to be flagged as a required enhancement for
    `lionfuncs`.
- **Risk:** Complexity in managing the lifecycle of `lionfuncs` components.
  - **Mitigation:** Ensure `lionfuncs` provides clear startup and shutdown
    procedures. Implement robust lifecycle management in `khive`'s main
    application setup and teardown.

## 10. Open Questions

- What are the precise configuration options for `lionfuncs.network.Executor`
  regarding rate limits (per-host, per-endpoint, global)?
- How does `lionfuncs.network.Executor` manage authentication details? Are they
  solely part of `EndpointConfig` or can the Executor be configured with default
  auth providers?
- What specific exceptions are raised by `lionfuncs.network.Executor` for
  different failure scenarios (rate limit, timeout, connection error, API
  error)?
- Does `lionfuncs.network.Executor` handle retries internally, and how
  configurable is this retry behavior?

## 11. Appendices

### Appendix A: Research References

- Issue #80: "Architecture: Define a layered resource control architecture with
  clear component responsibilities"
- Issue #100: "Architectural Refactor: Align Clients, Executor, Queue with New
  Design Philosophy"
- `TDS-100.md`: "Technical Design Specification: Migration to lionfuncs (Issue
  #100)"
- Conceptual `lionfuncs` Documentation (Network Executor Usage Guide, Network
  Client Guide, Async Operations Guide, lionfuncs.concurrency module
  documentation) - (Ref: `TDS-100.md`)
