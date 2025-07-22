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