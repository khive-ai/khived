---
title: "Research Report: Evaluation of `docling` for Text Extraction"
date: 2025-05-22
issue: "#27"
author: "@khive-researcher"
library_name: "docling"
---

## 1. Abstract

This report evaluates the Python library `docling` as a potential replacement
for the current multi-library approach (`PyPDF2`, `python-docx`, `html2text`)
for text extraction within the Khive Reader Microservice (Issue #27). The
research focuses on `docling`'s capabilities, ease of integration, dependencies,
performance, maintenance, and a comparative analysis. Findings suggest `docling`
is a powerful, actively maintained, AI-driven toolkit with extensive format
support, but its direct `asyncio` compatibility for core parsing operations is
not explicitly documented in readily available sources.

## 2. Introduction

The Khive Reader Microservice currently employs a combination of `PyPDF2`,
`python-docx`, and `html2text` for extracting text from various document
formats. A suggestion was made to explore `docling` as a unified alternative.
This report investigates `docling` to determine its suitability for our needs.

## 3. Research Questions & Findings

### 3.1. Capabilities

**What are `docling`'s capabilities regarding text extraction from various file
formats (PDF, DOCX, HTML, TXT, and potentially others)?**

`docling` is an AI-driven toolkit designed for comprehensive document
understanding and conversion. (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1, based
on exa:https://arxiv.org/html/2501.17887v1)

- **Supported Input Formats:**
  - PDF (with advanced parsing capabilities, including layout analysis)
    (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9;
    pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Images (including scanned documents, PNG, JPG) via OCR (EasyOCR, Tesseract)
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Microsoft Office (Word DOCX, PowerPoint PPTX)
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - HTML (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9;
    pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Plain TXT is implicitly supported as a simpler case of document processing.
- **Extraction Features:**
  - Advanced PDF understanding, layout analysis, and bounding boxes.
    (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9;
    pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Table structure recognition (e.g., using TableFormer).
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Reading order determination. (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Figure and caption matching. (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- **Output Formats:** Markdown, JSON, HTML.
  (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- **Other Capabilities:**
  - Designed for integration with Generative AI ecosystems (e.g., LangChain,
    LlamaIndex). (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9;
    pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Synthetic data generation. (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)
  - REST API wrappers via FastAPI (`docling-serve`).
    (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)
  - Fully local execution, suitable for sensitive data.
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)

The `docling-parse` repository (exa:https://github.com/DS4SD/docling-parse)
specifically mentions being a "Simple package to extract text with coordinates
from programmatic PDFs."

### 3.2. Ease of Use/Integration

**How easy is it to integrate `docling` into our existing Python/asyncio
environment?**

- `docling` provides Python APIs and is designed to be extensible.
  (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- It uses a unified `DoclingDocument` data model for consistent representation.
  (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- **Asyncio:** Direct, built-in `asyncio` support for its core
  parsing/extraction pipelines was not explicitly found in the search results or
  the arXiv paper summary (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1;
  pplx:4d94cc51-c3e5-4e34-9149-6f95a2f7ce1d). The `docling-serve` component uses
  FastAPI, which is async, but this is for serving models/pipelines, not
  necessarily an indicator that the core extraction logic is natively async.
- Integration into an `asyncio` environment would likely involve running
  `docling`'s synchronous processing tasks in a thread pool executor (e.g.,
  `asyncio.to_thread` in Python 3.9+) to avoid blocking the event loop. This is
  a common pattern but adds a layer of management.

### 3.3. Dependencies & Footprint

**What are its dependencies? How does its footprint compare to using individual
libraries?**

`docling` is modular. (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)

- **Core Components:**
  - `docling-core`: Defines Pydantic models for `DoclingDocument`.
    (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)
  - `docling-parser`: Backend PDF parser.
    (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)
  - `docling-parse` (exa:https://github.com/DS4SD/docling-parse) seems to be a
    key part for PDF text/coordinate extraction.
- **AI/OCR Dependencies:**
  - OCR engines: EasyOCR, Tesseract. (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - AI Models: Layout analysis models (e.g., from DocLayNet), TableFormer.
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
  - Likely underlying ML frameworks like PyTorch or TensorFlow.
    (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- **Footprint Comparison:**
  - Individual libraries (`PyPDF2`, `python-docx`, `html2text`) are generally
    lightweight with minimal dependencies each.
  - `docling`, with its AI models and broader capabilities, will have a
    significantly larger dependency footprint, especially if all its features
    (including OCR models, layout models, table models) are installed. This
    means larger container images and potentially more complex dependency
    management. However, its modular nature might allow for a more tailored
    installation if only specific parsers are needed, but this needs
    verification.

### 3.4. Performance

**Is there any information on its performance characteristics?**

- The arXiv paper (exa:https://arxiv.org/html/2501.17887v1) claims `docling`
  offers "fast execution" and is competitive with tools like "Marker".
  (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- It's designed to be efficient on commodity hardware, capable of processing
  "multiple pages/minutes". (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- OCR operations (EasyOCR, Tesseract) introduce overhead, impacting speed for
  scanned documents. (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- GPU acceleration can significantly improve processing time.
  (pplx:f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1)
- Specific benchmarks against `PyPDF2`, `python-docx`, etc., were not found in
  the initial searches. Performance will heavily depend on the document
  complexity and the specific `docling` pipeline/models used.

### 3.5. Maintenance/Activity

**How well-maintained and active is the `docling` project?**

- The project appears to be actively maintained.
- It originated from IBM Research Zurich and is now under the LF AI & Data
  Foundation. (pplx:42996b84-f4c3-4f36-8d0b-c7c3974d58d9)
- Recent PyPI releases:
  - `docling`: Version 1.20.0 released 2024-10-11
    (exa:https://pypi.org/project/docling/1.20.0/), with a more recent one
    listed as 2025-05-14 in another search
    (exa:https://pypi.org/project/docling/).
  - `docling-enhanced`: Version 2.32.0 released 2025-05-08
    (exa:https://pypi.org/project/docling-enhanced/2.32.0/).
  - `docling-core`: Version 2.28.1 released 2025-04-25
    (exa:https://pypi.org/project/docling-core/2.28.1/).
- The GitHub repository is `docling-project/docling`
  (exa:https://github.com/DS4SD/docling).
- An arXiv paper was published recently (Nov 2024, updated Jan 2025).
  (exa:https://arxiv.org/html/2501.17887v1)
- Recent blog posts and articles (April 2025) also indicate ongoing development
  and promotion.
  (exa:https://www.redhat.com/en/blog/docling-missing-document-processing-companion-generative-ai,
  exa:https://blog.gopenai.com/docling-enrichment-features-6d876a75f58a?gi=9c65bced3676&source=rss----7adf3c3694ff---4)

### 3.6. Comparison

**How does `docling` compare to the current approach (using `PyPDF2`,
`python-docx`, `html2text`) in terms of features, complexity, and potential
benefits/drawbacks for `khive`?**

| Feature              | Current Approach (`PyPDF2`, `python-docx`, `html2text`) | `docling`                                                                                                   |
| -------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Core Extraction**  | Handles basic text from PDF, DOCX, HTML.                | Handles basic text plus advanced features: layout, tables, OCR, reading order from a wider range of inputs. |
| **Format Support**   | PDF, DOCX, HTML. Limited for images/scans.              | PDF, DOCX, HTML, Images (scans), PPTX. More comprehensive.                                                  |
| **AI Features**      | None.                                                   | Rich AI-driven understanding (layout, tables, OCR).                                                         |
| **Output Structure** | Plain text primarily.                                   | Structured output (Markdown, JSON, HTML), `DoclingDocument` model with coordinates, layout info.            |
| **Dependencies**     | Relatively small, separate for each library.            | Larger, includes ML models and frameworks. Modular, but core + AI models will be substantial.               |
| **Complexity**       | Simpler to manage individual, focused libraries.        | More complex due to its broader scope and AI dependencies. Unified API could simplify usage code.           |
| **Footprint**        | Smaller.                                                | Significantly larger, especially with AI models.                                                            |
| **Performance**      | Generally fast for basic text extraction.               | Potentially slower for simple tasks due to AI overhead, but faster/better for complex docs. GPU beneficial. |
| **Asyncio Support**  | Libraries are generally synchronous.                    | Core parsing likely synchronous; async handling would be external (e.g., thread pool).                      |
| **Maintenance**      | Individual libraries have varying maintenance levels.   | Actively maintained, backed by LF AI & Data.                                                                |

**Potential Benefits for `khive` with `docling`:**

- Unified API for multiple document types.
- Advanced extraction capabilities (layout, tables, OCR) could enable richer
  features in the Reader service.
- Structured output could be more useful downstream.
- Active maintenance and backing by a foundation.

**Potential Drawbacks for `khive` with `docling`:**

- Increased dependency size and complexity.
- Potentially higher resource consumption (CPU/GPU, memory).
- Lack of clear native `asyncio` support for core parsing might require careful
  integration (thread pools).
- Overkill if only basic text extraction is needed for many common formats.

## 4. Risks & Mitigations

- **Risk:** Increased complexity and dependency footprint.
  - **Mitigation:** Evaluate if `docling`'s modularity allows for a minimal
    installation focusing only on needed parsers. Thoroughly test dependency
    resolution.
- **Risk:** Performance overhead for simple documents compared to lightweight
  parsers.
  - **Mitigation:** Benchmark `docling` against the current approach for
    representative Khive use cases.
- **Risk:** Lack of explicit native `asyncio` support for core parsing.
  - **Mitigation:** Implement and test `docling` operations within a thread pool
    executor in the `asyncio` environment. Assess any performance implications.
- **Risk:** Steeper learning curve for the team.
  - **Mitigation:** Allocate time for team members to familiarize themselves
    with `docling`'s API and concepts.

## 5. Recommendation

Based on the research:

**Option 1: Adopt `docling` (Recommended with Caveats)** `docling` offers a
significantly more powerful and future-proof solution for document processing
than the current collection of individual libraries. Its ability to handle
complex PDFs, images (via OCR), and extract structured information (layout,
tables) could unlock new capabilities for the Khive Reader Microservice and
downstream consumers. The active maintenance and backing by the LF AI & Data
foundation are also strong positives.

**Caveats & Next Steps if Adopting:**

1. **Verify Minimal Installation:** Investigate if `docling` can be installed
   with only the necessary parsing components (e.g., for PDF, DOCX, HTML without
   heavy AI models if not immediately needed for basic text) to manage the
   dependency footprint.
2. **Async Integration:** Prototype the integration within Khive's `asyncio`
   environment using a thread pool executor for `docling`'s synchronous parsing
   operations. Measure any performance impact.
3. **Benchmarking:** Conduct targeted benchmarks comparing `docling` (with an
   appropriate configuration) against the current `PyPDF2`, `python-docx`,
   `html2text` approach for common document types and sizes relevant to Khive.
4. **Resource Planning:** Be prepared for potentially higher resource
   (CPU/memory, optional GPU) requirements.

**Option 2: Continue with Individual Libraries (Fallback)** If the dependency
footprint of `docling` is deemed too large for the immediate benefits, or if
native `asyncio` support is a hard requirement and thread pool execution is
undesirable, then continuing with the current, simpler approach is viable for
basic text extraction. However, this limits future capabilities regarding
advanced document understanding.

**Recommendation: Proceed with a cautious adoption of `docling` (Option 1),
starting with the caveats outlined above.** The potential long-term benefits of
a unified, powerful, and well-maintained document processing library are
significant. A phased approach, perhaps initially using `docling` for PDF and
gradually replacing other parsers, could also be considered.

## 6. Conclusion

`docling` is a promising, actively developed library with extensive document
processing capabilities that go far beyond simple text extraction. While it
introduces a larger dependency footprint and questions around direct `asyncio`
integration for its core operations need careful handling, its potential to
enhance the Khive Reader Microservice is substantial. A thorough evaluation
through prototyping and benchmarking, as outlined in the recommendation, is
advised before full-scale adoption.

## Appendix A: Raw Search Data

**Perplexity Search 1 (ID: 914d21f5-71b6-4a50-aa19-bb069dde1042):** Query:
`python docling library text extraction capabilities dependencies performance maintenance comparison`

```json
{
  "success": true,
  "action_performed": "search",
  "content": {
    "id": "914d21f5-71b6-4a50-aa19-bb069dde1042",
    "model": "sonar",
    "created": 1747922503,
    "usage": {
      "prompt_tokens": 11,
      "completion_tokens": 667,
      "total_tokens": 678,
      "search_context_size": "low"
    },
    "citations": [
      "https://azbigmedia.com/business/top-python-libraries-for-text-extraction-from-pdfs/",
      "https://unstract.com/blog/extract-tables-from-pdf-python/",
      "https://www.tecmint.com/python-text-extraction-from-images/",
      "https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/",
      "https://pymupdf.readthedocs.io/en/latest/app4.html"
    ],
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": "The query seems to be about the \"docling\" library, but it appears there might be a confusion, as \"docling\" is not a well-known Python library for text extraction. However, I will provide information on popular Python libraries for text extraction, including their capabilities, dependencies, performance, and maintenance, as well as comparisons among them.\n\n## Overview of Popular Libraries\n\n### PyPDF2\n- **Capabilities**: PyPDF2 is primarily used for PDF file manipulation but can also extract text. It is user-friendly and lightweight but may require additional libraries for complex tasks like OCR or table extraction[1].\n- **Dependencies**: Requires Python 3.6 or later.\n- **Performance**: It is relatively lightweight but may not handle complex layouts well.\n- **Maintenance**: Actively maintained by the community.\n\n### PyMuPDF\n- **Capabilities**: Offers high-speed text extraction with advanced features like table detection and OCR support. It is particularly good at handling complex layouts and preserving document structure[4][5].\n- **Dependencies**: Requires Python 3.6 or later.\n- **Performance**: High-performance compared to other libraries like PyPDF2[5].\n- **Maintenance**: Actively maintained by the community.\n\n### LLMWhisperer\n- **Capabilities**: A cloud-based document processing API designed specifically for LLM applications. It combines advanced OCR, layout analysis, and text extraction capabilities[4].\n- **Dependencies**: Requires an API key and internet connectivity.\n- **Performance**: Excellent for complex layouts, tables, and form fields with minimal code setup[4].\n- **Maintenance**: Actively maintained by the developers.\n\n### Camelot, Tabula, Pdfplumber, and Pdftables\n- **Capabilities**: These libraries are used for extracting tables from PDFs. Pdfplumber is noted for its high accuracy and control over complex tables, while Camelot and Tabula are easier to use but may require adjustments for complex tables[2].\n- **Dependencies**: Vary depending on the specific library.\n- **Performance**: Pdfplumber and LLMWhisperer excel in handling complex tables[2].\n- **Maintenance**: Actively maintained by their respective communities.\n\n### Tesseract OCR (pytesseract) and Other OCR Libraries\n- **Capabilities**: Used for text extraction from images. Tesseract OCR is widely recognized for its accuracy[3].\n- **Dependencies**: Requires Tesseract OCR to be installed on the system.\n- **Performance**: Highly accurate but can be resource-intensive[3].\n- **Maintenance**: Actively maintained by the community.\n\n## Comparison\n\n- **Ease of Use**: PyPDF2 and Pdftables are user-friendly, while PyMuPDF and LLMWhisperer offer more advanced features.\n- **Accuracy**: PyMuPDF and LLMWhisperer are noted for their high accuracy in complex layouts and tables, whereas Tesseract OCR is highly accurate with images.\n- **Performance**: PyMuPDF is high-performance, while LLMWhisperer excels in complex document processing.\n- **Maintenance**: Most libraries are actively maintained, ensuring they remain up-to-date and supported.\n\nWithout specific information on \"docling,\" these libraries are the most commonly used for text extraction in Python, each with its strengths and weaknesses depending on the specific requirements of the task."
        },
        "delta": { "role": "assistant", "content": "" }
      }
    ]
  }
}
```

**Perplexity Search 2 (ID: 42996b84-f4c3-4f36-8d0b-c7c3974d58d9):** Query:
`Summarize capabilities, supported file types, and dependencies of the python library docling from site:github.com/DS4SD/docling`

```json
{
  "success": true,
  "action_performed": "search",
  "content": {
    "id": "42996b84-f4c3-4f36-8d0b-c7c3974d58d9",
    "model": "sonar",
    "created": 1747922543,
    "usage": {
      "prompt_tokens": 28,
      "completion_tokens": 424,
      "total_tokens": 452,
      "search_context_size": "low"
    },
    "citations": [
      "https://github.com/docling-project/docling",
      "https://github.com/docling-project",
      "https://github.com/docling-project/docling-core",
      "https://docling-project.github.io/docling/",
      "https://github.com/docling-project/docling-sdg"
    ],
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": "The Python library **Docling** is a powerful open-source package designed to simplify document processing and parsing across diverse file formats with advanced PDF understanding. It provides seamless integration with generative AI ecosystems, making it useful for preparing documents for generative AI workflows[1][2][4].\n\n## Capabilities\n- Simplifies document processing and parsing from multiple formats.\n- Advanced understanding and extraction from PDFs.\n- Supports integrations into generative AI pipelines.\n- Includes modules for synthetic data generation from documents.\n- Provides REST API wrappers (via FastAPI) for scalable job distribution.\n- Supports question-answer pair generation from passages within documents using AI models.\n- Offers tools based on Model Context Protocol (MCP) for document conversion, manipulation, and generation agents.\n\n## Supported File Types\nDocling supports a variety of document formats including but not limited to:\n- PDF (with advanced parsing capabilities)\n- HTML\n- DOCX\n\nAdditional support likely extends to other common textual and semi-structured formats given the focus on diverse input types typical in document processing[1][2][5].\n\n## Dependencies\nAs a modular project, Docling depends on several components:\n- **docling-core**: Defines data types using Python pydantic models essential for DoclingDocument representations[3].\n- **docling-parser**: Backend PDF parser responsible for detailed PDF content extraction[2].\n- **docling-sdg**: Tools leveraging generative AI models to create synthetic datasets from parsed documents; installable via pip (`pip install docling-sdg`)[5].\n  \nOther dependencies involve integration with FastAPI frameworks (`docling-serve`) for REST API functionality, IBM-powered AI models (`docling-ibm-models`), and various tooling libraries supporting the Model Context Protocol (`docling-mcp`).\n\nIn summary, Docling is an extensible library ecosystem centered around robust multi-format document parsing—especially PDFs—and advanced tooling that supports both practical processing tasks and synthetic data generation powered by state-of-the-art AI technologies developed initially by IBM Research Zurich under LF AI & Data Foundation stewardship[1][2]."
        },
        "delta": { "role": "assistant", "content": "" }
      }
    ]
  }
}
```

**Perplexity Search 3 (ID: 4d94cc51-c3e5-4e34-9149-6f95a2f7ce1d):** Query:
`python docling library asyncio integration performance benchmarks`

```json
{
  "success": true,
  "action_performed": "search",
  "content": {
    "id": "4d94cc51-c3e5-4e34-9149-6f95a2f7ce1d",
    "model": "sonar",
    "created": 1747922579,
    "usage": {
      "prompt_tokens": 8,
      "completion_tokens": 622,
      "total_tokens": 630,
      "search_context_size": "low"
    },
    "citations": [
      "https://github.com/netcan/asyncio/blob/master/docs/benchmark.md",
      "https://dev.to/leapcell/high-performance-python-asyncio-4jkj",
      "https://docs.python.org/3/library/asyncio.html",
      "https://pyperformance.readthedocs.io/benchmarks.html",
      "https://www.nucamp.co/blog/coding-bootcamp-backend-with-python-2025-python-in-the-backend-in-2025-leveraging-asyncio-and-fastapi-for-highperformance-systems"
    ],
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": "Python's `asyncio` library is a cornerstone for asynchronous programming, enabling concurrent code execution using async/await syntax. Regarding its integration, performance benchmarks, and improvements especially relevant to 2025, the following points summarize the current state based on recent sources:\n\n## asyncio Performance Benchmarks and Integration\n\n- **Core asyncio**: Python’s built-in `asyncio` library uses coroutines to handle I/O-bound and high-level structured network code efficiently. It enables writing asynchronous servers and clients that avoid blocking operations by awaiting futures or other coroutines[1][3].\n\n- **Benchmarking async workloads**: The Python Performance Benchmark Suite includes specific benchmarks such as `async_tree`, which tests `asyncio.gather()` over a deep branching structure simulating various loads:\n  - Pure async call overhead without real work.\n  - Async I/O simulated with delays (e.g., async sleep).\n  - Mixed CPU-bound plus I/O tasks.\n  \n  These benchmarks provide insight into how well asyncio manages concurrent tasks under different conditions, measuring overheads of task scheduling versus actual work done asynchronously[4].\n\n- **High-performance enhancements**\n  - Using alternative event loops like *uvloop* (a fast implementation of the event loop on top of libuv) can significantly improve throughput in networking contexts compared to default asyncio loops[1].\n  \n- **Integration benefits**\n  - Modern libraries and frameworks (notably FastAPI) leverage asyncio for efficient backend web service architectures. Real-world data shows FastAPI combined with asyncio can handle thousands of requests per second while maintaining responsiveness — mainly due to efficient asynchronous handling of network I/O and database queries[5].\n  \n- **Programming model improvements**:\n  Asyncio APIs like `asyncio.create_task()`, `asyncio.ensure_future()`, and easier coroutine management improve developer productivity while maintaining performance in concurrent execution scenarios typical for web servers or data streaming applications[2].\n\n## Summary Table\n\n| Aspect                      | Details                                         | Source(s)            |\n|-----------------------------|------------------------------------------------|----------------------|\n| Core functionality          | Coroutine-based concurrency via async/await    | [1][3]               |\n| Benchmark types             | Async call trees simulating no-op & IO + CPU   | [4]                  |\n| Performance optimization   | Use uvloop for faster event loop                | [1]                  |\n| Real-world backend impact   | Frameworks like FastAPI utilize it for >3000 RPS scalable backends with low latency      | [5]                  |\n| Programming ergonomics      | Functions like create_task(), ensure_future() aid task scheduling                     | [2]                  |\n\nIn conclusion, Python’s asyncio remains highly performant particularly when paired with optimizations such as uvloop. Its integration in popular asynchronous frameworks continues to enhance Python backend systems' ability to scale efficiently in modern environments demanding massive concurrency with minimal latency.\n\nFor exact microbenchmark numbers or side-by-side comparisons against other concurrency models/languages beyond what is publicly documented requires direct review of benchmark results from repositories such as the one on GitHub linked above or third-party test suites focusing on detailed load testing scenarios."
        },
        "delta": { "role": "assistant", "content": "" }
      }
    ]
  }
}
```

**Perplexity Search 4 (ID: f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1):** Query:
`Summarize key features, architecture, supported formats, dependencies, and performance aspects of Docling from the paper at https://arxiv.org/html/2501.17887v1`

```json
{
  "success": true,
  "action_performed": "search",
  "content": {
    "id": "f1e86ab5-f5fa-4226-9ce6-0e82a96b72b1",
    "model": "sonar",
    "created": 1747922624,
    "usage": {
      "prompt_tokens": 37,
      "completion_tokens": 842,
      "total_tokens": 879,
      "search_context_size": "low"
    },
    "citations": [
      "https://arxiv.org/abs/2501.17887",
      "https://arxiv.org/pdf/2501.17887",
      "https://arxiv.org/html/2501.17887v1",
      "https://huggingface.co/papers/2501.17887",
      "https://www.themoonlight.io/en/review/docling-an-efficient-open-source-toolkit-for-ai-driven-document-conversion"
    ],
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": "Docling is an open-source, MIT-licensed toolkit engineered for efficient AI-driven document conversion. Here is a structured summary of its key features, architecture, supported formats, dependencies, and performance aspects as described in the arXiv paper[3][4][5]:\n\n## Key Features\n\n- **Document Parsing:** Capable of parsing common formats such as PDFs, images (including scanned docs), Microsoft Office files (Word, PowerPoint), HTML, and more.\n- **Export Options:** Supports exporting to Markdown, JSON, and HTML.\n- **AI-Driven Processing:** Uses advanced AI for comprehensive document understanding:\n  - **Layout analysis** with bounding boxes for text and image arrangement.\n  - **Table structure recognition** using models like TableFormer for accurate table extraction.\n  - **OCR integration** (EasyOCR and Tesseract) to handle scanned documents.\n  - **Reading order determination**, figure extraction with caption matching.\n- **Unified Data Model:** Employs a DoclingDocument data model for consistent representation across all input types[3][4].\n- **Local Execution:** Fully local processing makes it suitable for sensitive data and air-gapped environments[3].\n- **Extensibility & Integration:** Modular architecture allows easy extension or customization; integrates well with frameworks like LangChain and LlamaIndex[3][4].\n- **Hardware Acceleration:** Can leverage GPUs to speed up processing.\n\n## Architecture\n\nDocling uses a pipeline-based architecture:\n\n- **StandardPdfPipeline**: For PDFs/images—orchestrates layout analysis OCR/table recognition models to reconstruct pages into DoclingDocuments[3].\n- **SimplePipeline**: For markup-based formats (Office/HTML)—handles initial parsing then applies optional enrichment models[3].\nBoth pipelines are extensible: users can subclass or clone default pipelines to customize model chains or add new features.\n\nIn the final stage (\"Assembly\"), results from each page are aggregated into the unified DoclingDocument. A post-processing model further corrects reading orders and matches figures with their captions.\n\n## Supported Formats\n\n| Input Formats                | Export Formats      |\n|------------------------------|---------------------|\n| PDF                          | Markdown            |\n| Images (scanned/PNG/JPG/etc.)| JSON                |\n| MS Office (Word/PowerPoint)  | HTML                |\n| HTML                         |                     |\n\n## Dependencies\n\nThe toolkit provides Python APIs but relies on several external libraries:\n-\n   - **(Python ecosystem):** Core dependencies include docling-core package plus integrations; no explicit list is given in the abstract but codebase would likely use PyTorch/TensorFlow at base layer when leveraging deep learning models mentioned above.\n   - **(OCR):**\n     - EasyOCR: multi-language OCR support\n     - Tesseract: alternative/traditional OCR engine\n   - **(AI Models):**\n     - Layout Analysis Model(s): e.g., derived from DocLayNet/others\n     - TableFormer: table structure recognition\n   -\n   Note that actual dependency versions may be tracked in the project's installation file—however those details are not specified in this paper summary alone.\n\n(For latest info refer directly to project GitHub/depends files upon release.)\n\n## Performance Aspects\n\nBenchmarking indicates strong competitive performance compared to other open-source conversion tools such as Marker. Key notes:\n-\n    -\n      • High efficiency on commodity hardware due to optimized inference routines; can process multiple pages/minutes depending on complexity & hardware resources available locally;\n      •\n        OCROverhead tradeoff exists between fidelity/speed—using Tesseract/EasyOCRBrings higher accuracy but slower throughput than non-Optical Character Recognition paths when handling Scans Or Imaged Documents Only;\n      •\n        Use Of GPU Acceleration Improves processing time significantly over CPU-only configurations where compatible infrastructure Is present;\n\nIn summary,\n> \"Docling delivers fast execution while preserving high-quality layout reconstruction thanks To its Unified Pipelines And intelligent use Of State-of-the-art neural architectures\"[5].\n\nThis modular approach combined With broad format support positions it As useful both standalone And embedded within larger Text/AI applications via popular dev frameworks such As Langchain Or llamaindex [3][4]."
        },
        "delta": { "role": "assistant", "content": "" }
      }
    ]
  }
}
```
