import mlx
import gc
import pandas as pd
import numpy as np
import networkx as nx

from collections import defaultdict

import plotly.graph_objects as go

from mlx_embedding_models.embedding import EmbeddingModel
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances

import sys
sys.path.insert(0, "../")
from config import MLX_EMBDEDDING_MODEL
from db import HindsightDB
from chromadb_tools import get_chroma_collection, query_chroma, chroma_search_results_to_df

db = HindsightDB()

gc.collect()
mlx.core.metal.clear_cache()

chroma_collection = get_chroma_collection(collection_name="news_titles")

chroma_get_res = chroma_collection.get(include=['embeddings', 'documents'])
titles = list(chroma_get_res['documents'])
title_embeddings = list(chroma_get_res['embeddings'])

similarity_matrix = cosine_similarity(title_embeddings)
distance_matrix = 1 - similarity_matrix
clustering = linkage(distance_matrix, method="average", metric="euclidean")

cluster_labels = None
last_height = None

def get_clusters_at_height(height):
    return fcluster(clustering, height, criterion='distance')

def get_cluster_descriptions(titles, title_embeddings, cluster_labels):
    cluster_to_embeddings = defaultdict(list)
    cluster_to_titles = defaultdict(list)
    for title, title_embedding, cluster_label in zip(titles, title_embeddings, cluster_labels):
        if cluster_label < 0:
            continue
        cluster_to_embeddings[cluster_label].append(title_embedding)
        cluster_to_titles[cluster_label].append(title)
    
    cluster_to_desciption = {}
    cluster_to_embedding = {}
    for cluster_label, cluster_embeddings in cluster_to_embeddings.items():
        distances = pairwise_distances(cluster_embeddings, metric='euclidean')
        medoid_index = np.argmin(np.sum(distances, axis=0)) # Get the most centroid item
        cluster_to_embedding[cluster_label] = cluster_embeddings[medoid_index]
        if len(cluster_embeddings) > 1:
            cluster_to_desciption[cluster_label] = f"Num articles: {len(cluster_embeddings)}. Centroid title: {cluster_to_titles[cluster_label][medoid_index]}"
        else:
            cluster_to_desciption[cluster_label] = f"Article Title: {cluster_to_titles[cluster_label][0]}"

    return cluster_to_desciption, cluster_to_embedding

def get_google_news_graph(cluster_labels=cluster_labels, edge_similarity_threshold=0.6):
    cluster_to_description, cluster_to_embedding = get_cluster_descriptions(titles, title_embeddings, cluster_labels)

    cluster_to_embedding = {c : e for c, e in sorted(cluster_to_embedding.items())}
    similarity_matrix = cosine_similarity(list(cluster_to_embedding.values()))
                                          
    G = nx.Graph()
    cluster_ids = list(cluster_to_embedding.keys())
    # Add nodes with attributes
    for cluster_id in cluster_ids:
        G.add_node(cluster_id, text=cluster_to_description[cluster_id], color="orange")

    # Add edges with weights
    for i in range(1, len(similarity_matrix)):
        for j in range(i + 1, len(similarity_matrix)):
            if similarity_matrix[i][j] > edge_similarity_threshold:  # Only add edges above the threshold
                G.add_edge(cluster_ids[i], cluster_ids[j], weight=similarity_matrix[i][j])
    return G

def navigate_down_google_news_graph(node_id, edge_similarity_threshold=0.6):
    global cluster_labels
    global last_height

    height = last_height / 2
    last_height = height

    new_cluster_labels = get_clusters_at_height(height=height)
    print(f"H: {height} Total Clusters: {len(set(new_cluster_labels))}")
    filtered_cluster_labels = list()
    for i, c in enumerate(new_cluster_labels):
        if cluster_labels[i] == node_id:
            filtered_cluster_labels.append(c)
        elif cluster_labels[i] < 0:
            filtered_cluster_labels.append(cluster_labels[i] - 1)
        else:
            filtered_cluster_labels.append(-1)
    cluster_labels = filtered_cluster_labels

    pos_cluster_labels = [c for c in cluster_labels if c > 0]
    if len(set(pos_cluster_labels)) == 1 and len(pos_cluster_labels) > 1: # Keep going down if cluster doesn't seperate at current level
        return navigate_down_google_news_graph(node_id=pos_cluster_labels[0], edge_similarity_threshold=edge_similarity_threshold)
    return get_google_news_graph(cluster_labels, edge_similarity_threshold=edge_similarity_threshold)

def initialize_google_news_graph(height=4, edge_similarity_threshold=0.6):
    global last_height
    global cluster_labels

    last_height = height
    cluster_labels = get_clusters_at_height(height=height)
    return get_google_news_graph(cluster_labels, edge_similarity_threshold=edge_similarity_threshold)

def search_google_news_graph(search_text="", edge_similarity_threshold=0.5, distance_threshold=0.8, top_n=100):
    chroma_collection = get_chroma_collection(collection_name="news_titles")

    if search_text == "":
        chroma_get_res = chroma_collection.get(include=['embeddings', 'documents'])
        titles = list(chroma_get_res['documents'])[:top_n]
        title_embeddings = list(chroma_get_res['embeddings'])[:top_n]

        similarity_matrix = cosine_similarity(title_embeddings)

        G = nx.Graph()
        # Add nodes with attributes
        for idx, title in enumerate([search_text] + titles):
            G.add_node(idx, text=title, color="orange")

        # Add edges with weights
        for i in range(len(similarity_matrix)):
            for j in range(i + 1, len(similarity_matrix)):
                if similarity_matrix[i][j] > edge_similarity_threshold:  # Only add edges above the threshold
                    G.add_edge(i, j, weight=similarity_matrix[i][j])
        return G
    
    embedding_model = EmbeddingModel.from_registry(MLX_EMBDEDDING_MODEL)
    search_text_embedding = embedding_model.encode([search_text]).tolist()
    chroma_search_results = chroma_collection.query(
            search_text_embedding,
            n_results=top_n,
            include=['embeddings', 'documents', 'distances', 'metadatas']
    )
    chroma_search_results_df = chroma_search_results_to_df(chroma_search_results)
    chroma_search_results_df = chroma_search_results_df.loc[chroma_search_results_df['distance'] <= distance_threshold]
    
    # chroma_get_res = chroma_collection.get(ids=list(chroma_search_results_df['id']), include=['embeddings', 'documents'])
    titles = list(chroma_search_results_df['document'])
    title_embeddings = list(chroma_search_results_df['embedding'])

    embeddings = search_text_embedding + title_embeddings

    similarity_matrix = cosine_similarity(embeddings)

    G = nx.Graph()
    # Add nodes with attributes
    for idx, title in enumerate([search_text] + titles):
        G.add_node(idx, text=title, color="blue" if idx == 0 else "orange")

    # Add edges with weights
    for i in range(len(similarity_matrix)):
        for j in range(i + 1, len(similarity_matrix)):
            if similarity_matrix[i][j] > edge_similarity_threshold:  # Only add edges above the threshold
                G.add_edge(i, j, weight=similarity_matrix[i][j])
    return G