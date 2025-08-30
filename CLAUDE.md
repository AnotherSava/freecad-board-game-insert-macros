# Project Coding Standards

## Variable Naming Convention

This Python project uses **camelCase** naming convention for variables instead of the typical Python snake_case convention. This design choice is made to maintain consistency and alignment with the FreeCAD library API, which predominantly uses camelCase naming.

### Examples:
- Use: `arcOffset`, `edgeVector`, `cornerToCenterUnit`
- Avoid: `arc_offset`, `edge_vector`, `corner_to_center_unit`

### Rationale:
- Maintains consistency with FreeCAD library methods and properties
- Provides a cohesive coding style when interfacing with FreeCAD APIs
- Improves code readability when mixing project code with FreeCAD library calls

When writing or modifying code in this project, please follow the camelCase convention for all new variable names.

## Import Guidelines

### Import Placement
All import statements should be placed at the top of the file, following Python PEP 8 conventions. Avoid adding import statements in the middle of functions or methods.

### Examples:
- **Good**: Place all imports at the top of the file
```python
import math
import Part
from FreeCAD import Vector
from dataclasses import dataclass

class MyClass:
    def myMethod(self):
        result = math.cos(angle)
```

- **Avoid**: Adding imports inside functions or methods
```python
class MyClass:
    def myMethod(self):
        import math  # Avoid this
        result = math.cos(angle)
```

### Rationale:
- Follows Python PEP 8 style guidelines
- Makes dependencies clear and visible at the beginning of the file
- Improves code readability and maintainability
- Prevents potential import-related performance issues

## Method Call Parameter Spacing

When calling methods with explicitly named parameters, add spaces before and after the "=" sign for improved readability.

### Examples:
- **Good**: Use spaces around equals in parameter assignments
```python
result = SomeClass(
    width = 10,
    height = 20,
    color = "blue"
)
```

- **Avoid**: No spaces around equals
```python
result = SomeClass(
    width=10,
    height=20,
    color="blue"
)
```

### Rationale:
- Improves visual separation between parameter names and values
- Enhances code readability when parameters span multiple lines
- Maintains consistency across the codebase