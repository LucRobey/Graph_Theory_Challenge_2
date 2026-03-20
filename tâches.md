# Challenge 2 Organization Tasks

# 1. Data Preparation & Network Construction

- [X] Clean Data: Filter out bots (e.g., AutoModerator) and deleted/anonymous accounts
- [X] Refine Edge Weights: Implement differentiated weights based on interaction type or size
- [X] Consolidate Graphs: Create an automated pipeline for generating directed adjacency matrices per subreddit and time window

## 2. Graph Modeling & Centrality Analysis

- [X] Community Detection: Implement Louvain or Leiden algorithms
- [X] Centrality Metrics: Calculate Betweenness and Eigenvector/PageRank centrality for users
- [X] Core-Periphery Structure: Apply models to identify the engagement "backbone"

## 3. Dynamic Analysis

- [ ] Temporal Tracking: Compute graph metrics dynamically using weekly segmentation
- [ ] Evolution Metrics: Track week-over-week changes (modularity, new leaders, network density)

## 4. Anomaly Detection & Alerting Mechanism

- [X] Define Heuristics: Combine metrics to flag anomalous users (e.g., centrality spikes + bridging)

## 5. Verification

- [ ] Robustness Testing: Simulate removal of core nodes and measure network fragmentation
- [ ] Metric Evaluation: Track global graph metrics before and after anomaly filtering
- [ ] Manual Verification: Qualitatively review the top flagged "anomalous" users
