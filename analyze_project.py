"""
Main script to analyze a Python project and generate function interaction graphs.
Usage: python analyze_project.py [project_path]
"""

import sys
import os
from pathlib import Path
from code_analyzer import CodeAnalyzer
from graph_visualizer import GraphVisualizer
import json


def main():
    """Main entry point for code analysis."""
    # Get project path
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    project_path = Path(project_path).resolve()
    
    if not project_path.exists():
        print(f"Error: Path '{project_path}' does not exist.")
        sys.exit(1)
    
    # Determine project folder name for results directory
    if project_path.is_file():
        # If it's a file, use the parent directory name
        project_folder_name = project_path.parent.name
    elif str(project_path) == "." or str(project_path) == Path.cwd():
        # If it's current directory, use current directory name
        project_folder_name = Path.cwd().name
    else:
        # Use the directory name itself
        project_folder_name = project_path.name
    
    # Create results directory name
    results_dir_name = f"{project_folder_name}_results"
    results_dir = Path(results_dir_name)
    results_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("PYTHON CODE ANALYZER - Function Interaction Mapper")
    print("=" * 80)
    print(f"Analyzing project: {project_path}")
    print(f"Results will be saved to: {results_dir}")
    print()
    
    # Analyze the project
    analyzer = CodeAnalyzer(str(project_path))
    analyzer.analyze()
    
    # Get graph data
    graph_data = analyzer.get_graph_data()
    
    print(f"\n✓ Output directory created: {results_dir}")
    
    # Save raw JSON data
    json_output = results_dir / "code_graph.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)
    print(f"✓ Graph data saved to: {json_output}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    visualizer = GraphVisualizer(graph_data)
    
    # HTML visualization
    html_output = visualizer.generate_html_visualization(str(results_dir / "code_graph.html"))
    print(f"✓ Interactive HTML visualization: {html_output}")
    
    # Text report
    report_output = visualizer.generate_text_report(str(results_dir / "code_analysis_report.txt"))
    print(f"✓ Text report: {report_output}")
    
    # DOT format output
    dot_output = visualizer.generate_dot_output(str(results_dir / "code_graph.dot"))
    print(f"✓ DOT format file: {dot_output}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nSummary:")
    summary = graph_data["summary"]
    print(f"  • {summary.get('total_folders', 0)} folders")
    print(f"  • {summary['total_files']} files analyzed")
    print(f"  • {summary.get('total_modules', 0)} modules")
    print(f"  • {summary['total_functions']} functions found")
    print(f"  • {summary['total_classes']} classes found")
    print(f"  • {summary['functions_that_are_called']} functions are called by others")
    print(f"  • {summary['functions_that_call_others']} functions call other functions")
    print(f"\nOutput files (saved in '{results_dir_name}' folder):")
    print(f"  • {json_output} - Raw graph data (JSON)")
    print(f"  • {html_output} - Interactive visualization (open in browser)")
    print(f"  • {report_output} - Text report for architects")
    print(f"  • {dot_output} - Graphviz DOT format (use with dot command)")
    print()


if __name__ == "__main__":
    main()

