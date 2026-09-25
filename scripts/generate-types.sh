#!/usr/bin/env bash
# Regenerate src/opentype/types/_generated.py from the committed openapi.json.
# Never hand-edit the output; change the server, regenerate the contract, then run this.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
uvx --from 'datamodel-code-generator==0.28.5' datamodel-codegen \
  --input "$here/openapi.json" --input-file-type openapi \
  --output-model-type pydantic_v2.BaseModel --base-class opentype._models.BaseModel \
  --target-python-version 3.9 --use-standard-collections --field-constraints \
  --enum-field-as-literal all --collapse-root-models --allow-extra-fields --use-schema-description \
  --disable-timestamp --custom-file-header '# Generated from openapi.json by scripts/generate-types.sh. Do not edit.' \
  --output "$here/src/opentype/types/_generated.py"
