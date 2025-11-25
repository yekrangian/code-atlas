# Python Code Analyzer - Function Interaction Mapper

A simple yet powerful tool to analyze Python projects and generate knowledge graphs showing function interactions, parameters, and dependencies. Designed for architects who need visibility into code structure and relationships.

## Features

- **Function Discovery**: Automatically scans all Python files in your project
- **Parameter Analysis**: Extracts and documents function parameters
- **Call Graph**: Maps which functions call which other functions
- **Dependency Tracking**: Identifies functions that are frequently called (high coupling)
- **Architect-Friendly Output**: Multiple visualization formats:
  - Interactive HTML visualization (browser-based)
  - Text report with statistics and insights

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Analyze the current directory:
```bash
python analyze_project.py
```

Analyze a specific project:
```bash
python analyze_project.py /path/to/your/project
```

### Output Files

The tool generates several output files:

1. **`code_graph.json`** - Raw graph data in JSON format
   - Contains all function information, relationships, and metadata
   - Can be used for custom analysis or integration with other tools

2. **`code_graph.html`** - Interactive visualization
   - Open in any web browser
   - Interactive network graph showing function relationships
   - Click nodes to see details
   - Drag to rearrange layout

3. **`code_analysis_report.txt`** - Text-based report
   - Summary statistics
   - Most depended-upon functions (high coupling indicators)
   - Functions with most calls (complexity indicators)
   - Functions organized by file
   - Function call chains

## What It Analyzes

- **Function Definitions**: Name, location (file + line), parameters, return types
- **Function Calls**: Which functions call which other functions
- **Dependencies**: Functions that are called by many others (high coupling)
- **Complexity Indicators**: Functions that call many others
- **Class Methods**: Distinguishes between standalone functions and class methods
- **Cross-File Relationships**: Tracks function calls across different files

## Example Output

### Summary Statistics
```
Total Files Analyzed:        15
Total Functions:             127
Total Classes:               8
Functions Being Called:      45
Functions Calling Others:    89
```

### Most Depended-Upon Functions
Shows functions with high coupling (called by many other functions) - potential refactoring candidates.

### Functions with Most Calls
Shows complex functions that call many others - potential complexity hotspots.

## Architecture Insights

The tool helps architects identify:

1. **High Coupling**: Functions called by many others (may need abstraction)
2. **Complex Functions**: Functions that call many others (may need decomposition)
3. **Isolated Functions**: Functions not called by others (dead code candidates)
4. **Cross-File Dependencies**: Functions that span multiple files (modularity issues)
5. **Parameter Complexity**: Functions with many parameters (may need refactoring)

## Customization

### Filter by File
Modify `graph_visualizer.py` to filter visualizations by specific files or patterns.

### Adjust Visualization
The HTML visualization uses vis.js and can be customized in `graph_visualizer.py`.

### Extend Analysis
The `CodeAnalyzer` class can be extended to:
- Track variable usage
- Analyze import dependencies
- Detect circular dependencies
- Generate architecture diagrams

## Limitations

- Does not track dynamic function calls (e.g., `getattr(obj, func_name)()`)
- Does not analyze runtime behavior
- Does not track function calls through decorators or metaclasses
- Static analysis only (no execution tracing)

## Requirements

- Python 3.7+
- networkx (required)

## License

This tool is provided as-is for code analysis purposes.

