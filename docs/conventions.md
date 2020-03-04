# Coding conventions

* Imports:
  * We use the `black` Python code formatter and `isort` for sorting imports.
  * We also use the following import style, which is not automatically checked:

```python
import random  # Standard modules come first (isort takes care of this).
import re      # Import the module only, not classes or functions.
import subprocess
from dataclasses import dataclass  # Exception: dataclass.
from dataclasses_json import DataClassJsonMixin  # Exception: DataClassJsonMixin.
from pathlib import Path  # Exception: Path.
from typing import Iterable, List, Optional # Exception: typing.
```

