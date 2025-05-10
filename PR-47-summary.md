# Fix 'Argument list too long' error in `khive fmt`

## Issue

When running `khive fmt` with a large number of files, the command fails with
`OSError: [Errno 7] Argument list too long: 'ruff'`. This occurs because the
command line argument length limit is being exceeded when passing all files to
the formatter at once.

## Solution

Implemented a batching mechanism in the `format_stack` function to process files
in smaller batches (500 files per batch), staying within the OS argument length
limits.

## Changes

1. Modified `format_stack` function in `src/khive/cli/khive_fmt.py` to process
   files in batches
2. Added proper error handling for each batch
3. Implemented early termination in non-check mode to maintain current behavior
4. Updated tests to verify the batching behavior

## Testing

- Added unit tests for batching logic and error handling
- Manually tested with 1000+ files to verify the fix works correctly
- All existing tests continue to pass

## Documentation

- Created implementation plan document:
  `reports/ip/IP-47-fix-argument-list-too-long-error.md`

Fixes #47
