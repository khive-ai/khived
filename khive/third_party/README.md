# Generated OpenAI Models

This directory contains generated schema files for OpenAI API models.

## OpenAI Models

The `openai_models.py` file is generated from the OpenAI API schema and is not
committed to the repository. It is generated during the build process.

### Generation Command

To generate the OpenAI models, use the following command:

```bash
# Use exact version to guarantee byte-for-byte generation
python -m pip install 'datamodel-code-generator[http]==0.30.1'

python -m datamodel-codegen \
  --url https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml \
  --output khive/third_party/openai_models.py \
  --allow-population-by-field-name \
  --output-model-type pydantic_v2.BaseModel \
  --field-constraints \
  --use-schema-description \
  --input-file-type openapi \
  --use-field-description \
  --use-one-literal-as-default \
  --enum-field-as-literal all \
  --use-union-operator \
  --no-alias
```

**Note**: if `bytes_aliased` and `float_aliased` are not generated, you can add
them manually onto the top of the file

```python
from typing import Annotated
from pydantic import Field

bytes_aliased = Annotated[bytes, Field(alias="bytes")]
float_aliased = Annotated[float, Field(alias="float")]
```

### Avoiding Pydantic Alias Warnings

After generation, add the following line at the top of the file to avoid
Pydantic alias warnings:

```python
from __future__ import annotations  # noqa: D401,F401
```

This prevents warnings about "alias must be outermost" that can appear if the
generated OpenAI models are imported before Pydantic's patched typing fix.

### Why Not Committed

The OpenAI schema file is large and frequently updated. Rather than committing
this large, auto-generated file to the repository, we generate it during the
CI/CD build process. This approach:

1. Keeps the repository size smaller
2. Makes it easier to update to the latest OpenAI API version
3. Avoids merge conflicts on auto-generated code
4. Follows best practices for generated code

### CI Integration

The file is generated as part of the pre-build step in CI, ensuring that the
wheel distribution still contains the models even though they're not in the
repository.
