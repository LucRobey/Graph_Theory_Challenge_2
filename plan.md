# Goal Description

The objective of this challenge is to analyze Reddit data to identify inappropriate behavior, manipulation, disinformation, and key influencers, assisting community managers in alignment with the Digital Services Act (DSA). We will build upon

![](vscode-file://vscode-app/c:/Users/Users/AppData/Local/Programs/Antigravity/resources/app/extensions/theme-symbols/src/icons/files/notebook.svg)

study_interactions.ipynb and follow `Méthodologie.docx` by creating interaction graphs, extracting topological features, and tracking them dynamically to alert moderators of anomalous activities.

## Proposed Changes

### Data Preparation & Network Construction

* **Clean Data** : Filter out known bots (e.g., `AutoModerator`, `RemindMeBot`) and deleted/anonymous accounts from the interaction dataframe.
* **Refine Edge Weights** : Introduce differentiated weights based on the interaction type. For instance, creating a post might have a different weight than commenting, or we can incorporate the length of the comment/post (bytes added) if available.
* **Consolidate Graphs** : Create an automated pipeline that generates the directed adjacency matrix for any given subreddit and time window (e.g., weekly).

### Graph Modeling & Centrality Analysis

* **Community Detection** : Implement the Louvain or Leiden algorithms (using `networkx` or `cdlib`) to identify modular communities within the subreddits.
* **Centrality Metrics** : Calculate key indicators for each node (user):
* *Betweenness Centrality* : To detect users bridging different communities (potential bottlenecks or key information diffusers).
* *Eigenvector/PageRank Centrality* : To identify the most prominent voices (leaders) being interacted with by other prominent voices.
* **Core-Periphery Structure** : Apply core-periphery models to separate the highly engaged "backbone" of the subreddit from casual participants.

### Dynamic Analysis

* **Temporal Tracking** : Use the `ISOYearWeek` segmentation to compute graph metrics dynamically.
* **Evolution Metrics** : Track the week-over-week change in modularity, the emergence of new leaders, or sudden shifts in network density that could indicate a coordinated campaign or brigading.

### Anomaly Detection & Alerting Mechanism

* **Define Heuristics** : Combine topological metrics to flag users. For example, a sudden spike in Betweenness Centrality combined with bridging disparate communities could indicate a troll or a raid leader.

## Verification Plan

### Automated/Analytical Verification

* **Robustness Testing** : Simulate the removal of identified "core" nodes and measure the resulting network fragmentation (e.g., tracking the size of the Largest Connected Component). This will prove whether the identified leaders actually are structural pillars of the community.
* **Metric Evaluation** : Track global graph metrics (like overall modularity) before and after filtering anomalies to ensure the networks make structural sense.

### Manual Verification

* **Qualitative Review** : Extract the top 10 most "anomalous" users or the most isolated sub-communities identified by the algorithms. The user can manually review their actual posts/comments in the dataset to confirm if the activity represents the target inappropriate behavior.
