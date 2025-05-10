---
title: "Implementation Plan: Fix 'Argument list too long' error in `khive fmt`"
issue: "#47"
author: "khive-implementer"
date: "2025-05-10"
status: "Implemented"
---

# Implementation Plan: Fix 'Argument list too long' error in `khive fmt`

## 1. Problem Statement

When running `khive fmt` with a large number of files, the command fails with
`OSError: [Errno 7] Argument list too long: 'ruff'`. This occurs because the
command line argument length limit is being exceeded when passing all files to
the formatter at once.

## 2. Proposed Solution

Implement a batching mechanism in the `format_stack` function within
`src/khive/cli/khive_fmt.py` to process files in smaller batches, staying within
the OS argument length limits.

### Key Components:

1. **Batch Processing**: Split the list of files into smaller batches (e.g., 500
   files per batch) and process each batch separately.
2. **Error Handling**: Ensure proper error handling for each batch, with
   appropriate status reporting.
3. **Early Termination**: In non-check mode, stop processing on the first error
   to maintain the current behavior.

## 3. Implementation Details

### 3.1 Changes to `format_stack` function

The main change will be in the `format_stack` function to process files in
batches:

1. Define a constant `MAX_FILES_PER_BATCH = 500` to limit the number of files
   processed in a single batch.
2. Split the file list into batches of at most `MAX_FILES_PER_BATCH` files.
3. Process each batch separately, accumulating results.
4. In non-check mode, stop processing on the first error.
5. In check mode, continue processing all batches even if errors are
   encountered.

### 3.2 Test Updates

Update the tests to verify the batching behavior:

1. Add a test for batching logic to ensure files are correctly split into
   batches.
2. Add a test for error handling in batched processing.

## 4. Implementation Steps

1. Modify the `format_stack` function to implement batching.
2. Update tests to verify the batching behavior.
3. Run tests to ensure the fix works correctly.
4. Verify the fix with a large number of files.

## 5. Testing Strategy

1. **Unit Tests**: Update existing tests to verify batching behavior.
2. **Manual Testing**: Create a large number of files and verify that
   `khive fmt` can process them without errors.

## 6. Implementation Notes

The implementation is straightforward and focused on the specific issue. The
batching approach is a common solution for command-line argument length
limitations.

## 7. References

- [Issue #47](https://github.com/khive-ai/khive.d/issues/47)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
