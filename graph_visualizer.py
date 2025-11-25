"""
Graph Visualizer - Creates architect-friendly visualizations
of function interactions and dependencies.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import networkx as nx
from collections import defaultdict


class GraphVisualizer:
    """Creates visualizations from code analysis data."""
    
    def __init__(self, graph_data: Dict):
        self.graph_data = graph_data
        self.graph = nx.DiGraph()
        self._build_networkx_graph()
    
    def _build_networkx_graph(self):
        """Build NetworkX graph from graph data."""
        # Add nodes
        for node in self.graph_data["nodes"]:
            # Create a copy of node dict without 'id' (used as node identifier)
            node_attrs = {k: v for k, v in node.items() if k != "id"}
            self.graph.add_node(node["id"], **node_attrs)
        
        # Add edges
        for edge in self.graph_data["edges"]:
            if edge["source"] in self.graph and edge["target"] in self.graph:
                self.graph.add_edge(
                    edge["source"],
                    edge["target"],
                    type=edge["type"],
                    relationship=edge["relationship"]
                )
    
    def generate_html_visualization(self, output_file: str = "code_graph.html"):
        """Generate interactive HTML visualization using vis.js."""
        nodes = []
        edges = []
        
        # Prepare nodes with different styles for each type
        for node in self.graph_data["nodes"]:
            node_type = node.get('type', 'function')
            node_id = node["id"]
            label = node['label']
            
            # Set color and shape based on node type
            if node_type == 'folder':
                color = '#D4E6F1'  # Light blue
                shape = 'box'
                title = f"Folder: {node.get('path', '')}\nFiles: {node.get('file_count', 0)}\nSubfolders: {node.get('subfolder_count', 0)}"
                value = max(node.get('file_count', 0), 1)
            elif node_type == 'file':
                # Different colors for Python vs non-Python files
                is_python = node.get('is_python', False)
                if is_python:
                    color = '#A9DFBF'  # Light green for Python files
                else:
                    color = '#D5DBDB'  # Light gray for non-Python files
                shape = 'box'
                extension = node.get('extension', '')
                module_info = f"\nModule: {node.get('module', '')}" if node.get('module') else ""
                func_info = f"\nFunctions: {node.get('function_count', 0)}" if is_python else ""
                title = f"File: {node.get('path', '')}\nType: {extension or 'no extension'}{module_info}{func_info}"
                value = max(node.get('function_count', 0), 1) if is_python else 1
            elif node_type == 'module':
                color = '#F9E79F'  # Light yellow
                shape = 'ellipse'
                title = f"Module: {node.get('name', '')}\nFile: {node.get('file', '')}\nFunctions: {node.get('function_count', 0)}\nClasses: {node.get('class_count', 0)}"
                value = max(node.get('function_count', 0), 1)
            else:  # function or method
                if node.get('class'):
                    label = f"{node['class']}.{label}"
                
                if node_type == 'method':
                    color = '#E1F5FF'  # Light blue
                else:
                    color = '#FFF4E1'  # Light beige
                
                if node.get('called_by_count', 0) > 5:
                    color = '#FFE1E1'  # Light red for high coupling
                
                shape = 'dot'
                title = (f"Function: {label}\nFile: {node.get('file', '')}\nModule: {node.get('module', '')}\nLine: {node.get('line', '')}\n"
                        f"Parameters: {node.get('parameter_count', 0)}\n"
                        f"Called by: {node.get('called_by_count', 0)} functions\n"
                        f"Calls: {node.get('call_count', 0)} functions")
                value = max(node.get('parameter_count', 0), node.get('called_by_count', 0), 1)
            
            node_data = {
                "id": node_id,
                "label": label,
                "title": title,
                "color": color,
                "shape": shape,
                "value": value,
                "type": node_type
            }
            nodes.append(node_data)
        
        # Prepare edges with different styles for different relationships
        for edge in self.graph_data["edges"]:
            edge_type = edge.get("type", "calls")
            relationship = edge.get("relationship", "")
            
            # Set color and style based on relationship type
            title = relationship.replace("_", " ").title()  # Default title
            
            if relationship == "folder_contains_file" or relationship == "folder_contains_folder":
                color = "#3498DB"  # Blue for containment
                dashes = False
                width = 2
            elif relationship == "file_defines_module":
                color = "#2ECC71"  # Green for definition
                dashes = False
                width = 2
            elif relationship == "module_contains_function":
                color = "#F39C12"  # Orange for module containment
                dashes = False
                width = 2
            elif relationship == "file_imports_from_file" or relationship == "module_imports_from_module":
                color = "#9B59B6"  # Purple for imports
                dashes = True
                width = 3
                # Add import details to title
                imports_list = edge.get("imports", [])
                is_relative = edge.get("is_relative", False)
                import_type = "relative" if is_relative else "absolute"
                title = f"Imports: {', '.join(imports_list[:3])}"
                if len(imports_list) > 3:
                    title += f" (+{len(imports_list) - 3} more)"
                title += f" ({import_type})"
            elif edge_type == "calls":
                color = "#848484"  # Gray for function calls
                dashes = False
                width = 1
                title = "Function Call"
            else:
                color = "#95A5A6"  # Light gray for other relationships
                dashes = True
                width = 1
            
            edges.append({
                "from": edge["source"],
                "to": edge["target"],
                "arrows": "to",
                "color": {"color": color},
                "dashes": dashes,
                "width": width,
                "title": title
            })
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Code Function Interaction Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        #mynetwork {{
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 8px;
        }}
        .header {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        .stat-item {{
            padding: 10px 15px;
            border-radius: 4px;
            border: 2px solid;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .stat-item::before {{
            content: '';
            width: 16px;
            height: 16px;
            border-radius: 3px;
            display: inline-block;
        }}
        .stat-folder {{
            background: #D4E6F1;
            border-color: #3498DB;
        }}
        .stat-folder::before {{
            background: #D4E6F1;
            border: 2px solid #3498DB;
        }}
        .stat-file {{
            background: #A9DFBF;
            border-color: #2ECC71;
        }}
        .stat-file::before {{
            background: #A9DFBF;
            border: 2px solid #2ECC71;
        }}
        .stat-module {{
            background: #F9E79F;
            border-color: #F39C12;
        }}
        .stat-module::before {{
            background: #F9E79F;
            border: 2px solid #F39C12;
        }}
        .stat-function {{
            background: #FFF4E1;
            border-color: #E67E22;
        }}
        .stat-function::before {{
            background: #FFF4E1;
            border: 2px solid #E67E22;
        }}
        .stat-class {{
            background: #E1F5FF;
            border-color: #3498DB;
        }}
        .stat-class::before {{
            background: #E1F5FF;
            border: 2px solid #3498DB;
        }}
        .legend-section {{
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 6px;
            border: 1px solid #ddd;
        }}
        .legend-title {{
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .edge-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 10px;
        }}
        .edge-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        .edge-line {{
            width: 40px;
            height: 3px;
            position: relative;
        }}
        .edge-line-solid {{
            border-top: 3px solid;
        }}
        .edge-line-dashed {{
            border-top: 3px dashed;
        }}
        .search-container {{
            margin-top: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            padding: 10px 15px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 6px;
            outline: none;
            transition: border-color 0.3s;
        }}
        .search-box:focus {{
            border-color: #3498DB;
        }}
        .search-button {{
            padding: 10px 20px;
            background: #3498DB;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }}
        .search-button:hover {{
            background: #2980B9;
        }}
        .search-info {{
            font-size: 12px;
            color: #666;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Python Code Function Interaction Graph</h1>
        <div class="stats">
            <div class="stat-item stat-folder"><strong>📁 Folders:</strong> {self.graph_data['summary'].get('total_folders', 0)}</div>
            <div class="stat-item stat-file"><strong>📄 Files:</strong> {self.graph_data['summary']['total_files']}</div>
            <div class="stat-item stat-module"><strong>📦 Modules:</strong> {self.graph_data['summary'].get('total_modules', 0)}</div>
            <div class="stat-item stat-function"><strong>⚙️ Functions:</strong> {self.graph_data['summary']['total_functions']}</div>
            <div class="stat-item stat-class"><strong>🏛️ Classes:</strong> {self.graph_data['summary']['total_classes']}</div>
        </div>
        <div class="legend-section">
            <div class="legend-title">Edge Types (Relationships):</div>
            <div class="edge-legend">
                <div class="edge-item">
                    <div class="edge-line edge-line-solid" style="border-color: #3498DB;"></div>
                    <span>Folder Contains</span>
                </div>
                <div class="edge-item">
                    <div class="edge-line edge-line-solid" style="border-color: #2ECC71;"></div>
                    <span>File Defines Module</span>
                </div>
                <div class="edge-item">
                    <div class="edge-line edge-line-solid" style="border-color: #F39C12;"></div>
                    <span>Module Contains Function</span>
                </div>
                <div class="edge-item">
                    <div class="edge-line edge-line-dashed" style="border-color: #9B59B6;"></div>
                    <span>Imports</span>
                </div>
                <div class="edge-item">
                    <div class="edge-line edge-line-solid" style="border-color: #848484;"></div>
                    <span>Function Calls</span>
                </div>
                <div class="edge-item">
                    <div class="edge-line edge-line-dashed" style="border-color: #95A5A6;"></div>
                    <span>Dependencies</span>
                </div>
            </div>
        </div>
        <div class="search-container">
            <input type="text" id="searchBox" class="search-box" placeholder="Search for functions, files, modules, or folders...">
            <button onclick="performSearch()" class="search-button">Search</button>
            <button onclick="clearSearch()" class="search-button" style="background: #95A5A6;">Clear</button>
            <span id="searchInfo" class="search-info"></span>
        </div>
    </div>
    <div id="mynetwork"></div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(edges)});
        
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                font: {{
                    size: 12
                }},
                borderWidth: 2,
                chosen: {{
                    node: function(values, id, selected, hovering) {{
                        values.borderWidth = 4;
                        values.borderColor = '#FF0000';
                    }}
                }},
                tooltip: {{
                    delay: 100,
                    template: function(nodeData) {{
                        // Convert newlines to HTML line breaks for proper display
                        var title = nodeData.title || '';
                        return title.replace(/\\n/g, '<br>');
                    }}
                }}
            }},
            edges: {{
                smooth: {{
                    type: 'continuous'
                }},
                width: 2
            }},
            physics: {{
                enabled: true,
                stabilization: {{
                    enabled: true,
                    iterations: 200,
                    onlyDynamicEdges: false,
                    fit: true
                }},
                barnesHut: {{
                    gravitationalConstant: -2000,
                    centralGravity: 0.1,
                    springLength: 200,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 0.5
                }},
                maxVelocity: 50,
                minVelocity: 0.1,
                solver: 'barnesHut',
                timestep: 0.5
            }},
            interaction: {{
                dragNodes: true,
                dragView: true,
                zoomView: true,
                selectConnectedEdges: true,
                hover: true
            }},
            layout: {{
                improvedLayout: true
            }}
        }};
        var network = new vis.Network(container, data, options);
        
        // Allow physics to stabilize initially, then disable for manual dragging
        network.on("stabilizationEnd", function() {{
            // Disable physics but keep dragging enabled
            network.setOptions({{ 
                physics: {{ enabled: false }},
                interaction: {{
                    dragNodes: true,
                    dragView: true,
                    zoomView: true
                }}
            }});
        }});
        
        // Ensure nodes are always draggable
        network.on("dragStart", function(params) {{
            // Ensure physics stays disabled during drag
            network.setOptions({{ physics: {{ enabled: false }} }});
        }});
        
        // Re-enable dragging after any physics changes
        network.on("stabilizationProgress", function() {{
            // Keep dragging enabled even during stabilization
            network.setOptions({{ 
                interaction: {{ dragNodes: true }}
            }});
        }});
        
        // Search functionality
        var allNodes = nodes.get();
        var allEdges = edges.get();
        
        function performSearch() {{
            var searchTerm = document.getElementById('searchBox').value.toLowerCase().trim();
            var searchInfo = document.getElementById('searchInfo');
            
            if (!searchTerm) {{
                clearSearch();
                return;
            }}
            
            // Find matching nodes
            var matchingNodeIds = [];
            var matchingNodes = [];
            
            allNodes.forEach(function(node) {{
                var label = (node.label || '').toLowerCase();
                var file = (node.file || '').toLowerCase();
                var module = (node.module || node.name || '').toLowerCase();
                var path = (node.path || '').toLowerCase();
                var id = (node.id || '').toLowerCase();
                
                if (label.includes(searchTerm) || 
                    file.includes(searchTerm) || 
                    module.includes(searchTerm) || 
                    path.includes(searchTerm) ||
                    id.includes(searchTerm)) {{
                    matchingNodeIds.push(node.id);
                    matchingNodes.push(node);
                }}
            }});
            
            if (matchingNodeIds.length === 0) {{
                searchInfo.textContent = 'No matches found';
                searchInfo.style.color = '#E74C3C';
                // Gray out all nodes
                var updateArray = allNodes.map(function(node) {{
                    return {{
                        id: node.id,
                        hidden: false,
                        opacity: 0.2,
                        color: {{
                            border: '#CCCCCC',
                            background: '#E8E8E8',
                            highlight: {{ border: '#CCCCCC', background: '#E8E8E8' }}
                        }}
                    }};
                }});
                nodes.update(updateArray);
                return;
            }}
            
            searchInfo.textContent = `Found ${{matchingNodeIds.length}} match(es)`;
            searchInfo.style.color = '#27AE60';
            
            // Find connected nodes
            var connectedNodeIds = new Set(matchingNodeIds);
            allEdges.forEach(function(edge) {{
                if (matchingNodeIds.includes(edge.from) || matchingNodeIds.includes(edge.to)) {{
                    connectedNodeIds.add(edge.from);
                    connectedNodeIds.add(edge.to);
                }}
            }});
            
            // Update all nodes: highlight matches, show connected, gray out others
            var updateArray = allNodes.map(function(node) {{
                var isMatch = matchingNodeIds.includes(node.id);
                var isConnected = connectedNodeIds.has(node.id) && !isMatch;
                
                if (isMatch) {{
                    // Matching nodes: full opacity, red border
                    return {{
                        id: node.id,
                        hidden: false,
                        opacity: 1,
                        color: {{
                            border: '#FF0000',
                            background: node.color || '#FFFFFF',
                            highlight: {{ border: '#FF0000', background: '#FFE1E1' }}
                        }}
                    }};
                }} else if (isConnected) {{
                    // Connected nodes: full opacity, blue border
                    return {{
                        id: node.id,
                        hidden: false,
                        opacity: 1,
                        color: {{
                            border: '#3498DB',
                            background: node.color || '#FFFFFF',
                            highlight: {{ border: '#3498DB', background: '#E1F5FF' }}
                        }}
                    }};
                }} else {{
                    // Other nodes: grayed out with reduced opacity
                    return {{
                        id: node.id,
                        hidden: false,
                        opacity: 0.2,
                        color: {{
                            border: '#CCCCCC',
                            background: '#E8E8E8',
                            highlight: {{ border: '#CCCCCC', background: '#E8E8E8' }}
                        }}
                    }};
                }}
            }});
            nodes.update(updateArray);
            
            // Fit to matching nodes
            network.fit({{
                nodes: matchingNodeIds,
                animation: true
            }});
        }}
        
        function clearSearch() {{
            document.getElementById('searchBox').value = '';
            document.getElementById('searchInfo').textContent = '';
            
            // Show all nodes with original colors and full opacity
            var updateArray = allNodes.map(function(node) {{
                return {{
                    id: node.id,
                    hidden: false,
                    opacity: 1,
                    color: node.color
                }};
            }});
            nodes.update(updateArray);
            
            // Reset view
            network.fit({{
                animation: true
            }});
        }}
        
        // Enable Enter key to search
        document.getElementById('searchBox').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                performSearch();
            }}
        }});
        
        // Real-time search as you type (optional - can be removed if too slow)
        var searchTimeout;
        document.getElementById('searchBox').addEventListener('input', function() {{
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {{
                if (document.getElementById('searchBox').value.trim()) {{
                    performSearch();
                }} else {{
                    clearSearch();
                }}
            }}, 300); // Wait 300ms after user stops typing
        }});
    </script>
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Interactive HTML visualization generated: {output_file}")
        return output_file
    
    def generate_dot_output(self, output_file: str = "code_graph.dot"):
        """Generate Graphviz DOT format file."""
        lines = []
        lines.append('digraph CodeGraph {')
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=rounded];')
        lines.append('')
        
        # Add nodes with appropriate shapes and colors
        for node in self.graph_data["nodes"]:
            node_type = node.get('type', 'function')
            node_id = node["id"].replace('::', '_').replace('.', '_').replace('\\', '_').replace('/', '_')
            label = node.get('label', '')
            
            # Set shape and color based on node type
            if node_type == 'folder':
                shape = 'box'
                color = '#D4E6F1'
                style = 'rounded,filled'
            elif node_type == 'file':
                shape = 'box'
                is_python = node.get('is_python', False)
                color = '#A9DFBF' if is_python else '#D5DBDB'
                style = 'rounded,filled'
            elif node_type == 'module':
                shape = 'ellipse'
                color = '#F9E79F'
                style = 'filled'
            else:  # function or method
                shape = 'ellipse'
                if node_type == 'method':
                    color = '#E1F5FF'
                else:
                    color = '#FFF4E1'
                style = 'filled'
            
            # Escape special characters in label
            label_escaped = label.replace('"', '\\"').replace('\n', ' ')
            
            # Format style with quotes if it contains a comma
            style_attr = f'"{style}"' if ',' in style else style
            
            lines.append(f'  "{node_id}" [label="{label_escaped}", shape={shape}, style={style_attr}, fillcolor="{color}"];')
        
        lines.append('')
        
        # Add edges with appropriate styles
        for edge in self.graph_data["edges"]:
            source_id = edge["source"].replace('::', '_').replace('.', '_').replace('\\', '_').replace('/', '_')
            target_id = edge["target"].replace('::', '_').replace('.', '_').replace('\\', '_').replace('/', '_')
            relationship = edge.get("relationship", "")
            edge_type = edge.get("type", "")
            
            # Set color and style based on relationship
            if relationship == "folder_contains_file" or relationship == "folder_contains_folder":
                color = "#3498DB"
                style = "solid"
            elif relationship == "file_defines_module":
                color = "#2ECC71"
                style = "solid"
            elif relationship == "module_contains_function":
                color = "#F39C12"
                style = "solid"
            elif relationship == "file_imports_from_file" or relationship == "module_imports_from_module":
                color = "#9B59B6"
                style = "dashed"
            elif edge_type == "calls":
                color = "#848484"
                style = "solid"
            else:
                color = "#95A5A6"
                style = "dashed"
            
            lines.append(f'  "{source_id}" -> "{target_id}" [color="{color}", style={style}];')
        
        lines.append('}')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"DOT format file generated: {output_file}")
        print(f"  To generate PNG: dot -Tpng {output_file} -o code_graph.png")
        print(f"  To generate SVG: dot -Tsvg {output_file} -o code_graph.svg")
        print(f"  To generate PDF: dot -Tpdf {output_file} -o code_graph.pdf")
        return output_file
    
    def generate_text_report(self, output_file: str = "code_analysis_report.txt"):
        """Generate a text-based report for architects."""
        lines = []
        lines.append("=" * 80)
        lines.append("PYTHON CODE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        summary = self.graph_data["summary"]
        lines.append("SUMMARY STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total Folders:               {summary.get('total_folders', 0)}")
        lines.append(f"Total Files Analyzed:        {summary['total_files']}")
        lines.append(f"Total Modules:               {summary.get('total_modules', 0)}")
        lines.append(f"Total Functions:             {summary['total_functions']}")
        lines.append(f"Total Classes:               {summary['total_classes']}")
        lines.append(f"Total Parameters:            {summary['total_parameters']}")
        lines.append(f"Functions with Docstrings:   {summary['functions_with_docstrings']}")
        lines.append(f"Functions Calling Others:    {summary['functions_that_call_others']}")
        lines.append(f"Functions Being Called:      {summary['functions_that_are_called']}")
        lines.append(f"Avg Parameters per Function: {summary['average_parameters_per_function']:.2f}")
        lines.append("")
        
        # Hierarchy structure
        if "hierarchy" in self.graph_data:
            lines.append("PROJECT HIERARCHY")
            lines.append("-" * 80)
            hierarchy = self.graph_data["hierarchy"]
            
            # Show folder structure
            def print_folder(folder_path, indent=0):
                if folder_path not in hierarchy["folders"]:
                    return
                folder_info = hierarchy["folders"][folder_path]
                folder_name = Path(folder_path).name if folder_path else "ROOT"
                lines.append("  " * indent + f"📁 {folder_name}/ ({len(folder_info['files'])} files, {len(folder_info['subfolders'])} subfolders)")
                
                # Print files in this folder
                for file_path in sorted(folder_info["files"]):
                    if file_path in hierarchy["files"]:
                        file_info = hierarchy["files"][file_path]
                        file_name = file_info['name']
                        extension = file_info.get("extension", "")
                        is_python = file_info.get("is_python", False)
                        
                        if is_python:
                            module_name = file_info.get("module", "")
                            func_count = len(file_info.get("functions", []))
                            lines.append("  " * (indent + 1) + f"🐍 {file_name} (Python - module: {module_name}, {func_count} functions)")
                            
                            # Show module details
                            if module_name in hierarchy["modules"]:
                                module_info = hierarchy["modules"][module_name]
                                class_count = len(module_info.get("classes", []))
                                if class_count > 0:
                                    lines.append("  " * (indent + 2) + f"   └─ Module: {module_name} ({class_count} classes)")
                        else:
                            lines.append("  " * (indent + 1) + f"📄 {file_name} ({extension or 'no extension'})")
                
                # Print subfolders
                for subfolder in sorted(folder_info["subfolders"]):
                    print_folder(subfolder, indent + 1)
            
            # Start from root folder
            print_folder("")
            lines.append("")
        
        # Most called functions (dependencies) - only functions
        lines.append("MOST DEPENDED-UPON FUNCTIONS (High Coupling)")
        lines.append("-" * 80)
        function_nodes = [n for n in self.graph_data["nodes"] if n.get('type') in ['function', 'method']]
        sorted_by_called = sorted(
            function_nodes,
            key=lambda x: x.get('called_by_count', 0),
            reverse=True
        )[:10]
        for i, node in enumerate(sorted_by_called, 1):
            if node.get('called_by_count', 0) > 0:
                lines.append(f"{i}. {node['label']} (in {node.get('file', '')})")
                lines.append(f"   Module: {node.get('module', '')}")
                lines.append(f"   Called by {node.get('called_by_count', 0)} functions")
                if node.get('class'):
                    lines.append(f"   Class: {node['class']}")
                lines.append("")
        
        # Functions with most calls (complexity indicators) - only functions
        lines.append("FUNCTIONS WITH MOST CALLS (Complexity Indicators)")
        lines.append("-" * 80)
        sorted_by_calls = sorted(
            function_nodes,
            key=lambda x: x.get('call_count', 0),
            reverse=True
        )[:10]
        for i, node in enumerate(sorted_by_calls, 1):
            if node.get('call_count', 0) > 0:
                lines.append(f"{i}. {node['label']} (in {node.get('file', '')})")
                lines.append(f"   Module: {node.get('module', '')}")
                lines.append(f"   Calls {node.get('call_count', 0)} other functions")
                if node.get('class'):
                    lines.append(f"   Class: {node['class']}")
                lines.append("")
        
        # Functions by folder/file/module
        lines.append("FUNCTIONS BY FOLDER / FILE / MODULE")
        lines.append("-" * 80)
        
        if "hierarchy" in self.graph_data:
            hierarchy = self.graph_data["hierarchy"]
            
            def print_folder_functions(folder_path, indent=0):
                if folder_path not in hierarchy["folders"]:
                    return
                folder_info = hierarchy["folders"][folder_path]
                folder_name = Path(folder_path).name if folder_path else "ROOT"
                lines.append("\n" + "  " * indent + f"📁 {folder_name}/")
                
                # Print files in this folder
                for file_path in sorted(folder_info["files"]):
                    if file_path in hierarchy["files"]:
                        file_info = hierarchy["files"][file_path]
                        file_name = file_info['name']
                        extension = file_info.get("extension", "")
                        is_python = file_info.get("is_python", False)
                        
                        if is_python:
                            module_name = file_info.get("module", "")
                            lines.append("  " * (indent + 1) + f"🐍 {file_name} (Python)")
                            
                            # Show module
                            if module_name in hierarchy["modules"]:
                                module_info = hierarchy["modules"][module_name]
                                lines.append("  " * (indent + 2) + f"   Module: {module_name}")
                                
                                # Show functions in this module
                                func_names = module_info.get("functions", [])
                                function_nodes = [n for n in self.graph_data["nodes"] 
                                               if n.get("id") in func_names and n.get("type") in ["function", "method"]]
                                
                                for func in sorted(function_nodes, key=lambda x: x.get('line', 0)):
                                    func_type = "method" if func.get('type') == 'method' else "function"
                                    func_label = func['label']
                                    if func.get('class'):
                                        func_label = f"{func['class']}.{func_label}"
                                    
                                    lines.append("  " * (indent + 3) + f"  • {func_label} ({func_type})")
                                    if func.get('parameters'):
                                        params_str = ", ".join(func['parameters'][:2])
                                        if len(func['parameters']) > 2:
                                            params_str += f", ... (+{len(func['parameters']) - 2} more)"
                                        lines.append("  " * (indent + 4) + f"    Params: {params_str}")
                                    if func.get('called_by_count', 0) > 0:
                                        lines.append("  " * (indent + 4) + f"    Called by: {func.get('called_by_count', 0)} functions")
                                    if func.get('call_count', 0) > 0:
                                        lines.append("  " * (indent + 4) + f"    Calls: {func.get('call_count', 0)} functions")
                        else:
                            lines.append("  " * (indent + 1) + f"📄 {file_name} ({extension or 'no extension'})")
                
                # Print subfolders
                for subfolder in sorted(folder_info["subfolders"]):
                    print_folder_functions(subfolder, indent + 1)
            
            print_folder_functions("")
        else:
            # Fallback to old format if hierarchy not available
            files_dict = defaultdict(list)
            for node in self.graph_data["nodes"]:
                if node.get('type') in ['function', 'method'] and node.get('file'):
                    files_dict[node['file']].append(node)
            
            for file_path, funcs in sorted(files_dict.items()):
                lines.append(f"\n{file_path} ({len(funcs)} functions)")
                for func in sorted(funcs, key=lambda x: x.get('line', 0)):
                    func_type = "method" if func.get('type') == 'method' else "function"
                    params_str = ", ".join(func.get('parameters', [])[:3])
                    if len(func.get('parameters', [])) > 3:
                        params_str += f", ... (+{len(func.get('parameters', [])) - 3} more)"
                    lines.append(f"  - {func['label']} ({func_type})")
                    if func.get('parameters'):
                        lines.append(f"    Parameters: {params_str}")
                    if func.get('called_by_count', 0) > 0:
                        lines.append(f"    Called by: {func.get('called_by_count', 0)} functions")
                    if func.get('call_count', 0) > 0:
                        lines.append(f"    Calls: {func.get('call_count', 0)} functions")
        
        # Import relationships
        if "imports" in self.graph_data:
            lines.append("")
            lines.append("IMPORT RELATIONSHIPS")
            lines.append("-" * 80)
            imports_data = self.graph_data["imports"]
            
            # Group by importing file
            for importing_file in sorted(imports_data.keys()):
                import_list = imports_data[importing_file]
                if not import_list:
                    continue
                
                lines.append(f"\n{importing_file} imports:")
                for import_info in import_list:
                    from_module = import_info.get("from", "")
                    resolved = import_info.get("resolved_module", "")
                    imported_items = import_info.get("imports", [])
                    is_relative = import_info.get("is_relative", False)
                    import_type = "relative" if is_relative else "absolute"
                    
                    items_str = ", ".join(imported_items[:5])
                    if len(imported_items) > 5:
                        items_str += f" (+{len(imported_items) - 5} more)"
                    
                    lines.append(f"  from {from_module} import {items_str}")
                    if resolved and resolved != from_module:
                        lines.append(f"    → Resolved to: {resolved}")
                    lines.append(f"    Type: {import_type}")
        
        # Function call chains
        lines.append("")
        lines.append("FUNCTION CALL CHAINS (Top 10)")
        lines.append("-" * 80)
        call_chains = []
        for edge in self.graph_data["edges"]:
            if edge["type"] == "calls":
                source_node = next(n for n in self.graph_data["nodes"] if n["id"] == edge["source"])
                target_node = next(n for n in self.graph_data["nodes"] if n["id"] == edge["target"])
                call_chains.append({
                    "from": source_node['label'],
                    "to": target_node['label'],
                    "from_file": source_node['file'],
                    "to_file": target_node['file']
                })
        
        for i, chain in enumerate(call_chains[:10], 1):
            lines.append(f"{i}. {chain['from']} -> {chain['to']}")
            if chain['from_file'] != chain['to_file']:
                lines.append(f"   Cross-file: {chain['from_file']} -> {chain['to_file']}")
        
        lines.append("")
        lines.append("=" * 80)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Text report generated: {output_file}")
        return output_file


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python graph_visualizer.py <code_graph.json>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    with open(json_file, 'r') as f:
        graph_data = json.load(f)
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    visualizer = GraphVisualizer(graph_data)
    visualizer.generate_html_visualization(str(results_dir / "code_graph.html"))
    visualizer.generate_text_report(str(results_dir / "code_analysis_report.txt"))
    visualizer.generate_dot_output(str(results_dir / "code_graph.dot"))

