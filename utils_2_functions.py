import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import networkx as nx


def measure_grades(node_metrics, dynamic_metrics):
    import pandas as pd
    
    def to_pct(col):
        """Safely converts a raw metric into a 0.0 to 1.0 percentile rank."""
        return col.rank(pct=True)

    def normalize_to_anomaly_score(col):
        """
        1. Ranks values (0.0 to 1.0)
        2. Cubes the rank to heavily penalize/suppress normal user scores 
        and aggressively highlight the extreme tail (anomalies).
        """
        ranks = to_pct(col)
        
        # 50th percentile node gets 0.5^3  = 0.125
        # 99th percentile node gets 0.99^3 = 0.970 
        return ranks ** 3

    # --- 1. Spammer ---
    node_metrics['Spammer_Ratio'] = node_metrics['Out_degree'] / (node_metrics['In_degree'] + 0.01)
    node_metrics['Grade_Spammer'] = normalize_to_anomaly_score(node_metrics['Spammer_Ratio'])
    # --- 2. Artificial Bridger Grade ---
    # Important: Convert to percentiles BEFORE doing math on them!
    bc_pct = to_pct(node_metrics['Betweenness_Score'])
    pr_pct = to_pct(node_metrics['PageRank_Score'])
    node_metrics['Grade_Bridger'] = normalize_to_anomaly_score((bc_pct + (1 - pr_pct)) / 2)
    # --- 3. Peripheral Yeller ---
    deg_pct = to_pct(node_metrics['Degree'])
    core_pct = to_pct(node_metrics['Coreness_Level'])
    node_metrics['Grade_Peripheral'] = normalize_to_anomaly_score((deg_pct + (1 - core_pct)) / 2)
    # --- 4. Sudden Leader Grade ---
    leader_counts = dynamic_metrics[dynamic_metrics['Leader_Changed'] == 1]['Top_Leader'].value_counts()
    node_metrics['Leader_Events'] = node_metrics['User'].map(leader_counts).fillna(0)
    node_metrics['Grade_Leader'] = (node_metrics['Leader_Events'] * 5).clip(upper=10) / 10
    # --- 5. Burstiness (Volatility) ---
    all_comments = pd.read_csv('all_comments.csv')
    # Extract Year-Week to group by
    all_comments['Date & Time'] = pd.to_datetime(all_comments['Date & Time'])
    all_comments['ISOYearWeek'] = all_comments['Date & Time'].dt.strftime('%G-W%V')
    user_weekly = all_comments.groupby(['Author', 'ISOYearWeek']).size().reset_index(name='Weekly_Count')
    user_burstiness = user_weekly.groupby('Author')['Weekly_Count'].agg(['max', 'mean']).reset_index()
    # Assuming `user_weekly` logic above this point stayed the same
    user_burstiness['Burst_Ratio'] = user_burstiness['max'] / (user_burstiness['mean'] + 0.1)
    user_burstiness['Grade_Burstiness'] = normalize_to_anomaly_score(user_burstiness['Burst_Ratio'])
    user_burstiness = user_burstiness.rename(columns={'Author': 'User'})
    node_metrics = node_metrics.merge(user_burstiness[['User', 'Grade_Burstiness']], on='User', how='left').fillna({'Grade_Burstiness': 0})
    # --- 6. Instability Leaders ---
    # We consider a week "unstable" if the absolute structural changes are in the extreme 5%
    dynamic_metrics['Abs_Delta_Density'] = dynamic_metrics['Delta_Density'].abs()
    dynamic_metrics['Abs_Delta_Modularity'] = dynamic_metrics['Delta_Modularity'].abs()
    density_thresh = dynamic_metrics['Abs_Delta_Density'].quantile(0.95)
    mod_thresh = dynamic_metrics['Abs_Delta_Modularity'].quantile(0.95)
    # Isolate the highly unstable events
    unstable_weeks = dynamic_metrics[
        (dynamic_metrics['Abs_Delta_Density'] >= density_thresh) | 
        (dynamic_metrics['Abs_Delta_Modularity'] >= mod_thresh)
    ]
    # Flag the users who were Top_Leader during these unstable weeks
    unstable_leaders = unstable_weeks['Top_Leader'].value_counts().reset_index()
    unstable_leaders.columns = ['User', 'Unstable_Leader_Events']
    unstable_leaders['Grade_Instability'] = normalize_to_anomaly_score(unstable_leaders['Unstable_Leader_Events'])
    node_metrics = node_metrics.merge(unstable_leaders[['User', 'Grade_Instability']], on='User', how='left').fillna({'Grade_Instability': 0})
    # --- 7. Coordinated Bot Ring / Astroturfing ---
    trans_pct = to_pct(node_metrics['Transitivity'])
    core_pct = to_pct(node_metrics['Coreness_Level'])
    pr_pct = to_pct(node_metrics['PageRank_Score'])
    a = (trans_pct + core_pct + (1 - pr_pct)) / 3
    node_metrics['Grade_BotRing'] = normalize_to_anomaly_score(a)


    # Total Score
    node_metrics['Total_Anomaly_Score'] = (node_metrics['Grade_Spammer'] + 
                                        node_metrics['Grade_Bridger'] + 
                                        node_metrics['Grade_Peripheral']+
                                        1.8*node_metrics['Grade_Leader']+
                                        node_metrics['Grade_Burstiness']+
                                        4*node_metrics['Grade_Instability']+
                                        node_metrics['Grade_BotRing'])

    # Define Threshold (e.g., Top 1%)
    threshold = node_metrics['Total_Anomaly_Score'].quantile(0.99)
    print(f"Threshold (99th percentile): {threshold:.2f}")

    # Plot score distribution
    plt.figure()
    sns.histplot(node_metrics['Total_Anomaly_Score'], bins=50, kde=True )
    plt.axvline(threshold, color='red', linestyle='--', label=f'Threshold ({threshold:.1f})')
    plt.title('Distribution of Total Anomaly Scores')
    plt.xlabel('Score (0-4)')
    plt.legend()
    plt.show()

    return node_metrics



def detect_dynamic_anomalies(node_metrics , global_threshold , nb_of_flags):
    # 1. Define distinct thresholds for each behavior 
    # (e.g., 0.90 means they are in the top 10% most suspicious for that specific trait)
    node_metrics['Is_Spammer']    = (node_metrics['Grade_Spammer'] > 0.80).astype(int)
    node_metrics['Is_Bridger']    = (node_metrics['Grade_Bridger'] > 0.85).astype(int)
    node_metrics['Is_Peripheral'] = (node_metrics['Grade_Peripheral'] > 0.85).astype(int)
    node_metrics['Is_Leader']     = (node_metrics['Grade_Leader'] > 0.4).astype(int)
    node_metrics['Is_Bursty']     = (node_metrics['Grade_Burstiness'] > 0.80).astype(int)
    node_metrics['Is_Unstable']   = (node_metrics['Grade_Instability'] > 0.60).astype(int)
    node_metrics['Is_BotRing']    = (node_metrics['Grade_BotRing'] > 0.95).astype(int)

    # 2. Count how many distinct 'Red Flags' this user raised
    flag_columns = ['Is_Spammer', 'Is_Bridger', 'Is_Peripheral', 'Is_Leader', 
                    'Is_Bursty', 'Is_Unstable', 'Is_BotRing']
    node_metrics['Total_Red_Flags'] = node_metrics[flag_columns].sum(axis=1)

    # 3. Create your Global Decision Rule
    # A user is an anomaly if they triggered multiple behavioral flags, 
    # OR if their continuous global score is exceptionally high.
    def is_anomaly(row):
        # Rule A: The Multi-Offender (e.g., they are a Spammer AND part of a BotRing)
        if row['Total_Red_Flags'] >= nb_of_flags:
            return True
        
        # Rule B: The Extreme Outlier (They just have a massive continuous pooled score)
        # (Assuming Total_Anomaly_Score is scaled 0 to 10)
        if row['Total_Anomaly_Score'] >= global_threshold: 
            return True
            
        return False

    node_metrics['Flagged_Anomaly'] = node_metrics.apply(is_anomaly, axis=1)
    # Flag anomalies
    anomalous_df = node_metrics[node_metrics['Flagged_Anomaly'] == True]
    anomalous_users = anomalous_df['User'].dropna().unique().tolist()

    print(f"Total anomalous users flagged: {len(anomalous_users)}")



    # Set an aesthetic style for the plots
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # --- 1. Distribution of Total Anomaly Scores ---
    # Shows the long tail of anomalies. Most users should be on the left
    sns.histplot(data=node_metrics, x='Total_Anomaly_Score', bins=50, kde=True, ax=axes[0, 0], color='royalblue')
    axes[0, 0].set_title('Distribution of Total Anomaly Scores', fontsize=14)
    axes[0, 0].set_xlabel('Total Anomaly Score')
    axes[0, 0].set_ylabel('Number of Users')
    if 'Total_Anomaly_Score' in node_metrics.columns:
        # Add a visual cutoff line at the 99th percentile
        cutoff = node_metrics['Total_Anomaly_Score'].quantile(0.99)
        axes[0, 0].axvline(x=cutoff, color='crimson', linestyle='--', label=f'Top 1% Cutoff ({cutoff:.2f})')
        axes[0, 0].legend()

    # --- 2. Flag Counts (If you implemented the Voting approach) ---
    if 'Total_Red_Flags' in node_metrics.columns:
        # Using log-scale because 90% of users will have 0 flags
        sns.countplot(data=node_metrics, x='Total_Red_Flags', ax=axes[0, 1], palette='Reds')
        axes[0, 1].set_title('Number of Users by Red Flag Count', fontsize=14)
        axes[0, 1].set_xlabel('Number of Flags Triggered')
        axes[0, 1].set_ylabel('Number of Users (Log Scale)')
        axes[0, 1].set_yscale('log') 

    # --- 3. Top 15 Most Anomalous Users ---
    # Ranks the absolute worst offenders
    top_15 = node_metrics.nlargest(15, 'Total_Anomaly_Score').copy()
    # Ensure User is string for categorical plotting
    top_15['User_Str'] = top_15['User'].astype(str)
    sns.barplot(data=top_15, x='Total_Anomaly_Score', y='User_Str', ax=axes[1, 0], palette='magma')
    axes[1, 0].set_title('Top 15 Most Anomalous Users', fontsize=14)
    axes[1, 0].set_xlabel('Total Anomaly Score')
    axes[1, 0].set_ylabel('User ID')

    # --- 4. Correlation Heatmap ---
    # Shows if certain bad behaviors happen together (e.g. are Spammers also Bursty?)
    grade_columns = [col for col in node_metrics.columns if col.startswith('Grade_')]
    corr = node_metrics[grade_columns].corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1, ax=axes[1, 1])
    axes[1, 1].set_title('Correlation Between Anomalous Behaviors', fontsize=14)

    plt.tight_layout()
    plt.show()

    # ==========================================================
    # BONUS: Radar Profile of the #1 Most Anomalous User
    # ==========================================================
    top_user = top_15.iloc[0]

    # Prepare the data
    labels = [col.replace('Grade_', '') for col in grade_columns]
    values = top_user[grade_columns].values.tolist()

    # Close the circle mathematically
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, color='crimson', linewidth=2, linestyle='solid')
    ax.fill(angles, values, color='crimson', alpha=0.3)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight='bold')
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=8)
    ax.set_ylim(0, 1) # Grades are capped at 1.0

    ax.set_title(f"Behavioral Profile: User {top_user['User']}", size=16, y=1.1, weight='bold')
    plt.show()

    return anomalous_users , node_metrics


from nltk.sentiment.vader import SentimentIntensityAnalyzer

def compare_anomalies(anomalous_users , alert_users):

    print("Loading all comments...")
    all_comments = pd.read_csv('all_comments.csv')

    # Filter for anomalous users
    anomalous_comments = all_comments[all_comments['Author'].isin(anomalous_users)].copy()
    print(f"Extracted {len(anomalous_comments)} comments generated by the anomalous users.")

    # Drop missing content
    anomalous_comments.dropna(subset=['Content'], inplace=True)
    
    # Initialize VADER
    sia = SentimentIntensityAnalyzer()

    def get_compound_sentiment(text):
        try:
            return sia.polarity_scores(str(text))['compound']
        except:
            return 0.0

    print("Calculating sentiment polarity for anomalous users' comments...")
    anomalous_comments['Sentiment_Compound'] = anomalous_comments['Content'].apply(get_compound_sentiment)

    # Let's also do a random sample of normal users for comparison
    normal_users = set(all_comments['Author'].unique()) - set(anomalous_users)
    sample_normal_users = list(normal_users)[:min(1000,len(anomalous_users),len(normal_users))]
    normal_comments = all_comments[all_comments['Author'].isin(sample_normal_users)].copy()
    normal_comments.dropna(subset=['Content'], inplace=True)

    print("Calculating sentiment polarity for a random sample of normal users...")
    normal_comments['Sentiment_Compound'] = normal_comments['Content'].apply(get_compound_sentiment)
    
    print("nb de normal users : ",len(normal_users))
    print("nb de anomalous users : ",len(anomalous_users))
    print("nb de alert users : ",len(alert_users))


    
    alert_comments = all_comments[all_comments['Author'].isin(alert_users)].copy()

    alert_comments.dropna(subset=['Content'], inplace=True)
    alert_comments['Sentiment_Compound'] = alert_comments['Content'].apply(get_compound_sentiment)

    alert_user_sentiment = alert_comments.groupby('Author')['Sentiment_Compound'].mean().reset_index()
    alert_user_sentiment['Group'] = 'Alert (Flagged)'


    # Aggregate by user
    anomalous_user_sentiment = anomalous_comments.groupby('Author')['Sentiment_Compound'].mean().reset_index()
    anomalous_user_sentiment['Group'] = 'Anomalous (Flagged)'

    normal_user_sentiment = normal_comments.groupby('Author')['Sentiment_Compound'].mean().reset_index()
    normal_user_sentiment['Group'] = 'Normal (Baseline Sample)'

    comparison_df = pd.concat([anomalous_user_sentiment, normal_user_sentiment,alert_user_sentiment])

    # Plot the distribution of average sentiment scores
    plt.figure(figsize=(10, 6))
    sns.histplot(data=comparison_df, x='Sentiment_Compound', hue='Group', kde=True, bins=30, common_norm=False)
    plt.title("Distribution of User Average Sentiment: Anomalous vs Normal Users")
    plt.axvline(np.mean(list(anomalous_user_sentiment["Sentiment_Compound"])), color='blue', linestyle='--')
    plt.axvline(np.mean(list(normal_user_sentiment["Sentiment_Compound"])), color='orange', linestyle='--')
    plt.axvline(np.mean(list(alert_user_sentiment["Sentiment_Compound"])), color='green', linestyle='--')


    plt.xlabel("Average Compound Sentiment (-1 = Most Negative, +1 = Most Positive)")
    plt.ylabel("Frequency")
    plt.show()

    # Print Top 10 most negative anomalous users
    negative_anomalous = anomalous_user_sentiment.sort_values(by='Sentiment_Compound').head(10)
    print("Top 10 Most Negative Anomalous Users:")
    display(negative_anomalous)
    
    

def test_graph_improvement(G_original, anomalous_users):
    print("Creating clean graph...")
    # 1. Create the clean graph by removing flagged users
    G_clean = G_original.copy()
    
    # Filter out anomalous users that actually exist in the graph
    nodes_to_remove = [u for u in anomalous_users if u in G_clean.nodes()]
    G_clean.remove_nodes_from(nodes_to_remove)
    
    print("\n=== BASIC STATS ===")
    n_orig = G_original.number_of_nodes()
    e_orig = G_original.number_of_edges()
    
    n_clean = G_clean.number_of_nodes()
    e_clean = G_clean.number_of_edges()
    
    pct_nodes_removed = (n_orig - n_clean) / n_orig * 100
    pct_edges_removed = (e_orig - e_clean) / e_orig * 100
    
    print(f"Nodes Removed: {len(nodes_to_remove)} ({pct_nodes_removed:.2f}% of network)")
    print(f"Edges Removed: {e_orig - e_clean} ({pct_edges_removed:.2f}% of network)")
    if pct_edges_removed > (pct_nodes_removed * 3):
        print("💡 INSIGHT: Highly disproportionate edge removal. These were likely spammers/hubs!")

    print("\n=== STRUCTURAL HEALTH ===")
    # Density
    print(f"Density Before: {nx.density(G_original):.5f}")
    print(f"Density After:  {nx.density(G_clean):.5f}")
    
    # Assortativity (Degree correlation)
    assort_orig = nx.degree_assortativity_coefficient(G_original)
    assort_clean = nx.degree_assortativity_coefficient(G_clean)
    print(f"\nAssortativity Before: {assort_orig:.4f}")
    print(f"Assortativity After:  {assort_clean:.4f}")
    if assort_clean > assort_orig:
        print("💡 INSIGHT: Assortativity increased. The network is behaving more like a natural human network.")
        
    # Giant Component Size (using undirected for safety)
    G_orig_undir = G_original.to_undirected()
    G_clean_undir = G_clean.to_undirected()
    
    gc_orig = max(nx.connected_components(G_orig_undir), key=len)
    gc_clean = max(nx.connected_components(G_clean_undir), key=len)
    
    print(f"\nGiant Component Before: {len(gc_orig)} nodes ({(len(gc_orig)/n_orig)*100:.1f}%)")
    print(f"Giant Component After:  {len(gc_clean)} nodes ({(len(gc_clean)/n_clean)*100:.1f}%)")
    
    # Note: Clustering can take a minute on very large graphs.
    print("\nCalculating Average Clustering (This may take a moment)...")
    clust_orig = nx.average_clustering(G_orig_undir)
    clust_clean = nx.average_clustering(G_clean_undir)
    
    print(f"Avg Clustering Before: {clust_orig:.4f}")
    print(f"Avg Clustering After:  {clust_clean:.4f}")
    if clust_clean > clust_orig:
        print("💡 INSIGHT: Clustering increased! Local communities are much tighter and less polluted after removing anomalies.")
        
    return G_clean
