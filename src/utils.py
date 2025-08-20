import matplotlib.pyplot as plt
import networkx as nx

def plot_graph(G, title = "Graph Visualization"):
    """Plot a NetworkX graph with specific colors for tables and fields."""
    # Create a dictionary for node labels (tables and columns)
    labels = {}
    for node in G.nodes():
        if 'tableName' in G.nodes[node]:
            labels[node] = G.nodes[node]['tableName']
        elif 'columnName' in G.nodes[node]:
            labels[node] = G.nodes[node]['columnName']
        else:
            labels[node] = str(node)  # Default to the node ID as label

    color_map = []
    for node in G.nodes():
        if 'tableName' in G.nodes[node]:  # Tables are red
            color_map.append('red')
        elif 'columnName' in G.nodes[node]:  # Columns are green
            color_map.append('green')
        else:  # Other nodes are blue
            color_map.append('blue')

    try:
        # Define graph layout using Graphviz's 'neato' algorithm
        pos = nx.nx_agraph.graphviz_layout(G, prog='neato')
    except ImportError:
        # Fallback to a different layout if pygraphviz is not available
        pos = nx.spring_layout(G)

    plt.rcParams['figure.figsize'] = [20, 20]  # Set figure size
    nx.draw(G, pos, labels=labels, node_color=color_map, with_labels=True)  # Draw the graph with labels and colors
    plt.title(title)  # Add a title to the plot
    plt.show()  # Display the plot

# Call the function to visualize the graph (ensure G is defined elsewhere)
plot_graph(G)

