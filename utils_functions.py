import networkx as nx
import pandas as pd
from networkx import community
import matplotlib.pyplot as plt
import seaborn as sns

def build_graph_from_data(edges_path):
    """
    Loads the datasets and builds a Graph where nodes are authors 
    and edges represent interactions (comments on posts).
    """
    # Load datasets
    df_edges = pd.read_csv(edges_path)
    
    # Standardizing columns: Linking commenters (Source) to post authors (Target)
    # Based on your previous logic, we ensure the graph captures user-to-user interaction
    G_directed = nx.DiGraph()
    for _, row in df_edges.iterrows():
            G_directed.add_edge(row['Source'], row['Target'], weight=row['Weight'])

    G = nx.from_pandas_edgelist(
        df_edges, 
        source='Source', 
        target='Target', 
        create_using=nx.Graph(),
        edge_attr='Weight'
    )
    
    print(f"Graph initialized: {G.number_of_nodes()} users, {G.number_of_edges()} interactions.")
    return G , G_directed


def detect_communities(G):
    """
    Implements the Louvain algorithm to identify modular communities.
    Returns a dictionary mapping {User: Community_ID}.
    """
    # Louvain algorithm for modularity optimization
    communities_list = nx.community.louvain_communities(G, seed=42)
    
    # Convert list of sets to a flat dictionary mapping
    community_mapping = {node: i for i, comm in enumerate(communities_list) for node in comm}
    
    print(f"Community Detection: Found {len(communities_list)} distinct groups.")
    return community_mapping

def calculate_centrality(G):
    """
    Calculates Betweenness (bridges) and PageRank (influencers).
    """
    print("Calculating Betweenness Centrality (using sampling for speed)...")
    # k=500 provides a good approximation for large graphs
    betweenness = nx.betweenness_centrality(G, k=500, seed=42)
    
    print("Calculating PageRank Centrality...")
    pagerank = nx.pagerank(G)
    
    return betweenness, pagerank

def calcultate_transitivity(G):

    transitivity = nx.clustering(G)

    return transitivity

def identify_core_periphery(G):
    """
    Applies k-core decomposition to separate the highly engaged 
    'backbone' from casual participants.
    """
    # core_number returns the highest k-core each node belongs to
    core_numbers = nx.core_number(G)
    return core_numbers


    metrics = []
    for node in G_directed.nodes():
        metrics.append({
            'User': node,
            'Betweenness_Centrality': betweenness.get(node, 0),
            'PageRank': pagerank.get(node, 0),
            'Community_ID': louvain_partition.get(node, -1),
            'Core_Number': core_numbers.get(node, 0),
        })

def generate_degree_metrics(G):
    metrics = []
    for node in G.nodes():
        metrics.append({
            'Degree': G.degree(node),
        })
    return pd.DataFrame(metrics)

def generate_directed_report(G_directed):

    deg_dict = dict(G_directed.degree())
    in_deg_dict = dict(G_directed.in_degree())
    out_deg_dict = dict(G_directed.out_degree())
    

    communities = detect_communities(G_directed)
    betweenness, pagerank = calculate_centrality(G_directed)
    core_scores = identify_core_periphery(G_directed)
    transitivity = calcultate_transitivity(G_directed)

    nodes = list(G_directed.nodes())

    
    return pd.DataFrame({
        'User': nodes,
        'Community_ID': [communities.get(node) for node in nodes],
        'Betweenness_Score': [betweenness.get(node, 0) for node in nodes],
        'PageRank_Score': [pagerank.get(node, 0) for node in nodes],
        'Coreness_Level': [core_scores.get(node, 0) for node in nodes],
        'Degree': [deg_dict.get(node, 0) for node in nodes],
        'In_degree': [in_deg_dict.get(node, 0) for node in nodes],
        'Out_degree': [out_deg_dict.get(node, 0) for node in nodes],
        'Transitivity' : [transitivity.get(node,0) for node in nodes]
    })

def generate_report(G):
    
    deg_dict = dict(G.degree())
    communities = detect_communities(G)
    betweenness, pagerank = calculate_centrality(G)
    core_scores = identify_core_periphery(G)
    nodes = list(G.nodes())

    
    return pd.DataFrame({
        'User': nodes,
        'Community_ID': [communities.get(node) for node in nodes],
        'Betweenness_Score': [betweenness.get(node, 0) for node in nodes],
        'PageRank_Score': [pagerank.get(node, 0) for node in nodes],
        'Coreness_Level': [core_scores.get(node, 0) for node in nodes],
        'Degree': [deg_dict.get(node, 0) for node in nodes],
    })
    

def generate_analysis_report(G , G_directed):
    """
    Executes all analyses and merges them into a single analytical DataFrame.
    """
    directed_report = generate_directed_report(G_directed)
    undirected_report = generate_report(G)

 
    
    # Label Core vs Periphery (Top 10% of coreness is considered the backbone)
    core_threshold = undirected_report['Coreness_Level'].quantile(0.9)
    undirected_report['Network_Role'] = undirected_report['Coreness_Level'].apply(
        lambda x: 'Core (Backbone)' if x >= core_threshold else 'Periphery'
    )

    return  undirected_report  , directed_report

def detect_anomalies(node_report, betweenness_threshold=0.8, pagerank_threshold=0.2):
    """
    Identifies suspicious users based on topological heuristics.
    - Potential Raid Leader: High Betweenness + High Coreness + Low PageRank.
    - Bridge/Troll: High Betweenness + Linking different communities.
    """
    
    # Normalize metrics between 0 and 1 for easier heuristic comparison
    metrics = ['Betweenness_Score', 'PageRank_Score', 'Coreness_Level']
    node_report_norm = node_report.copy()
    for m in metrics:
        node_report_norm[m] = (node_report[m] - node_report[m].min()) / (node_report[m].max() - node_report[m].min())

    alerts = []

    for index, row in node_report_norm.iterrows():
        # HEURISTIC 1: The "Raid Leader" / "Bridge Troll"
        # High Betweenness (top 10%) but relatively low PageRank (not a community pillar)
        if row['Betweenness_Score'] > node_report_norm['Betweenness_Score'].quantile(betweenness_threshold):
            if row['PageRank_Score'] < node_report_norm['PageRank_Score'].quantile(pagerank_threshold):
                alerts.append({
                    'User': row['User'],
                    'Type': 'Potential Bridge/Troll',
                    'Reason': 'High influence as a bridge but low community authority (PageRank).',
                    'Severity': 'High'
                })

        # HEURISTIC 2: Coordinated Backbone Member
        # High Coreness but very low PageRank (could be a bot or "sleeper" account)
        if row['Coreness_Level'] == 1.0 and row['PageRank_Score'] < 0.05:
            alerts.append({
                'User': row['User'],
                'Type': 'Suspicious Core Member',
                'Reason': 'Deeply embedded in the network backbone but has zero organic influence.',
                'Severity': 'Medium'
            })

    return pd.DataFrame(alerts)

def alert_community_manager(alerts_df):
    """
    Formats the alerts for a human Community Manager or DSA review.
    """
    if alerts_df.empty:
        print("✅ No suspicious patterns detected in this snapshot.")
    else:
        print(f"🚨 ALERT: {len(alerts_df)} suspicious users flagged for DSA review.")
        print("-" * 30)
        print(alerts_df.sort_values(by='Severity'))


def test_network_robustness(G, core_nodes):
    """
    Simulates the removal of core nodes and measures the impact on 
    the Largest Connected Component (LCC).
    """
    # Initial State
    initial_lcc_size = len(max(nx.connected_components(G), key=len))
    
    # Simulation: Remove identified core nodes
    G_fragmented = G.copy()
    G_fragmented.remove_nodes_from(core_nodes)
    
    # Final State
    final_lcc_size = len(max(nx.connected_components(G_fragmented), key=len)) if G_fragmented.nodes() else 0
    
    drop_percentage = ((initial_lcc_size - final_lcc_size) / initial_lcc_size) * 100
    
    print("--- Robustness Testing (Structural Pillars) ---")
    print(f"Initial LCC Size: {initial_lcc_size}")
    print(f"LCC Size after Core Removal: {final_lcc_size}")
    print(f"Network Fragmentation: {drop_percentage:.2f}% drop in connectivity.")
    
    return drop_percentage

def evaluate_filtering_impact(G, anomaly_nodes, community_mapping):
    """
    Compares global graph metrics (Modularity) before and after 
    filtering identified anomalies.
    """
    # Helper to convert mapping {node: cid} to list of sets [{n1, n2}, {n3}]
    def get_partition_list(nodes_to_keep, mapping):
        communities = {}
        for node in nodes_to_keep:
            cid = mapping[node]
            if cid not in communities: communities[cid] = set()
            communities[cid].add(node)
        return list(communities.values())

    # Initial Modularity
    initial_nodes = list(G.nodes())
    partition_initial = get_partition_list(initial_nodes, community_mapping)
    mod_initial = nx.community.modularity(G, partition_initial)
    
    # Filter Anomalies
    G_filtered = G.copy()
    G_filtered.remove_nodes_from(anomaly_nodes)
    
    # Final Modularity
    filtered_nodes = list(G_filtered.nodes())
    partition_filtered = get_partition_list(filtered_nodes, community_mapping)
    mod_filtered = nx.community.modularity(G_filtered, partition_filtered)
    
    print("\n--- Metric Evaluation (Noise Filtering) ---")
    print(f"Original Modularity: {mod_initial:.4f}")
    print(f"Filtered Modularity: {mod_filtered:.4f}")
    print(f"Improvement: {((mod_filtered - mod_initial) / mod_initial) * 100:.2f}%")
    
    return mod_initial, mod_filtered



def compute_weekly_metrics(G,df_sub):
    weeks = sorted(df_sub['ISOYearWeek'].unique())
    weekly_metrics = []
    
    for week in weeks:
        df_week = df_sub[df_sub['ISOYearWeek'] == week]
        
        # Build Directed and Undirected Graph
        if len(df_week) < 2:
            continue
            
        G.remove_edges_from(nx.selfloop_edges(G))
        G_undirected = G.to_undirected()
        
        # 1. Density
        density = nx.density(G)
        
        # 2. Modularity
        try:
            partition = community_louvain.best_partition(G_undirected, weight='weight')
            modularity = community_louvain.modularity(partition, G_undirected)
        except:
            modularity = 0.0
            
        # 3. Top Leader (by PageRank)
        try:
            pagerank = nx.pagerank(G_directed, weight='weight')
            if len(pagerank) > 0:
                top_leader = max(pagerank, key=pagerank.get)
                top_score = pagerank[top_leader]
            else:
                top_leader = None
                top_score = 0.0
        except:
            top_leader = None
            top_score = 0.0
            
        weekly_metrics.append({
            'ISOYearWeek': week,
            'Num_Nodes': len(G_directed.nodes()),
            'Num_Edges': len(G_directed.edges()),
            'Density': density,
            'Modularity': modularity,
            'Top_Leader': top_leader,
            'Top_Leader_Score': top_score
        })
        
    return pd.DataFrame(weekly_metrics)


def compute_weekly_metrics(df_sub):
    weeks = sorted(df_sub['ISOYearWeek'].unique())
    weekly_metrics = []
    
    for week in weeks:
        df_week = df_sub[df_sub['ISOYearWeek'] == week]
        
        # Build Directed and Undirected Graph
        if len(df_week) < 2:
            continue
            
        G_directed = nx.DiGraph()
        for _, row in df_week.iterrows():
            G_directed.add_edge(row['Source'], row['Target'], weight=row['Weight'])
        G_directed.remove_edges_from(nx.selfloop_edges(G_directed))
        G_undirected = G_directed.to_undirected()
        
        # 1. Density
        density = nx.density(G_directed)
        
        # 2. Modularity
        try:
            partition = community_louvain.best_partition(G_undirected, weight='weight')
            modularity = community_louvain.modularity(partition, G_undirected)
        except:
            modularity = 0.0
            
        # 3. Top Leader (by PageRank)
        try:
            pagerank = nx.pagerank(G_directed, weight='weight')
            if len(pagerank) > 0:
                top_leader = max(pagerank, key=pagerank.get)
                top_score = pagerank[top_leader]
            else:
                top_leader = None
                top_score = 0.0
        except:
            top_leader = None
            top_score = 0.0
            
        weekly_metrics.append({
            'ISOYearWeek': week,
            'Num_Nodes': len(G_directed.nodes()),
            'Num_Edges': len(G_directed.edges()),
            'Density': density,
            'Modularity': modularity,
            'Top_Leader': top_leader,
            'Top_Leader_Score': top_score
        })
        
    return pd.DataFrame(weekly_metrics)

def compute_all_weekly_metrics(edges_file):
    
    edges_df = pd.read_csv(edges_file)
    subreddits = edges_df['Subreddit'].unique()

    all_dynamic_metrics = []

    for subreddit in subreddits:
        print(f"Processing Subreddit: {subreddit}...")
        df_sub = edges_df[edges_df['Subreddit'] == subreddit]
        
        # Compute metrics for each available week
        weekly_metrics_df = compute_weekly_metrics(df_sub)
        if len(weekly_metrics_df) == 0:
            continue
            
        weekly_metrics_df['Subreddit'] = subreddit
        
        # Compute Week-over-Week Changes (Evolution Metrics)
        weekly_metrics_df['Delta_Density'] = weekly_metrics_df['Density'].diff().fillna(0)
        weekly_metrics_df['Delta_Modularity'] = weekly_metrics_df['Modularity'].diff().fillna(0)
        
        # Leader change flag
        weekly_metrics_df['Leader_Changed'] = (weekly_metrics_df['Top_Leader'] != weekly_metrics_df['Top_Leader'].shift(1)).astype(int)
        # The first week should technically not be a 'change' since there's no prior week, or we can leave it as 1 to indicate initiation.
        
        all_dynamic_metrics.append(weekly_metrics_df)
        
    final_dynamic_df = pd.concat(all_dynamic_metrics, ignore_index=True)

    # Rearrange columns
    cols = ['Subreddit', 'ISOYearWeek', 'Num_Nodes', 'Num_Edges', 'Density', 'Delta_Density', 
            'Modularity', 'Delta_Modularity', 'Top_Leader', 'Top_Leader_Score', 'Leader_Changed']
    final_dynamic_df = final_dynamic_df[cols]

    # Save to CSV
    final_dynamic_df.to_csv('graphs/dynamic_metrics.csv', index=False)
    print("Finished processing temporal graphs and saved to 'graphs/dynamic_metrics.csv'.")
    return final_dynamic_df


def plot_subreddit_metrics(final_dynamic_df, sub_name):
    sub_data = final_dynamic_df[final_dynamic_df['Subreddit'] == sub_name]
    
    fig, axes = plt.subplots(2, 2, figsize=(21, 12))

    # Modularity
    axes[0][0].plot(sub_data['ISOYearWeek'], sub_data['Modularity'], marker='o')
    axes[0][0].set_title(f'Modularity Evolution in r/{sub_name}')
    axes[0][0].tick_params(axis='x', rotation=45)
    axes[0][0].grid(True)

    # Density
    axes[0][1].plot(sub_data['ISOYearWeek'], sub_data['Density'], marker='o', color='orange')
    axes[0][1].set_title(f'Density Evolution in r/{sub_name}')
    axes[0][1].tick_params(axis='x', rotation=45)
    axes[0][1].grid(True)

    # Num Nodes
    axes[1][1].plot(sub_data['ISOYearWeek'], sub_data['Num_Nodes'], marker='o', color='green')
    axes[1][1].set_title(f'Num Nodes in r/{sub_name}')
    axes[1][1].tick_params(axis='x', rotation=45)
    axes[1][1].grid(True)

    plt.tight_layout()
    plt.show()


    