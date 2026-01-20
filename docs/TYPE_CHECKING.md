# Type Checking Guide

## Running Type Checks

### Check entire project
```bash
mypy .
```

### Check specific app
```bash
mypy character/
```

### Check specific file
```bash
mypy character/models/character.py
```

## Common Type Annotations

### Django Models
```python
from django.db.models.manager import RelatedManager
from typing import Optional

class MyModel(models.Model):
    name: str = models.CharField(max_length=100)
    optional_field: Optional[str] = models.CharField(null=True, blank=True)
    related: RelatedManager[OtherModel] = models.ManyToManyField(OtherModel)
```

### Views
```python
from django.http import HttpRequest, HttpResponse, JsonResponse

def my_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
```

### Serializers
```python
from rest_framework import serializers
from typing import Any, Dict

class MySerializer(serializers.ModelSerializer):
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return attrs
```

## Gradual Adoption Strategy

1. **Phase 1**: Infrastructure setup ✅
2. **Phase 2**: Type core models and utilities
3. **Phase 3**: Type views and serializers
4. **Phase 4**: Enable strict mode module-by-module
5. **Phase 5**: Full project coverage

## Ignoring Type Errors (Use Sparingly)

```python
# Ignore single line
result = some_untyped_function()  # type: ignore

# Ignore specific error
result = some_function()  # type: ignore[arg-type]
```

## Resources

- [mypy documentation](https://mypy.readthedocs.io/)
- [django-stubs](https://github.com/typeddjango/django-stubs)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
