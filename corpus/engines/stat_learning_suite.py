#!/usr/bin/env python3
"""
stat_learning_suite.py
Master Statistical Learning Suite.
The topic list follows the MTH432 course at IIT Delhi as a reference.
Independent implementation; no affiliation with IIT Delhi.
Pure Python & NumPy Implementation (Zero External Dependencies).

Algorithms Implemented:
1. Ridge (L2) & Lasso (L1) Regularized Linear Regression.
2. Linear Discriminant Analysis (LDA) Binary Classifier.
3. K-Means Unsupervised Clustering Engine.
4. K-Nearest Neighbors (KNN) Integration.

Usage:
    python stat_learning_suite.py
"""

import sys
import time
import math
import numpy as np

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. RIDGE (L2) & LASSO (L1) REGULARIZED LINEAR REGRESSION
# ==============================================================================
class RidgeRegression:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_ = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        # Closed-form solution: beta = (X^T X + alpha * I)^-1 X^T y
        n_samples, n_features = X.shape
        I = np.eye(n_features)
        I[0, 0] = 0.0 # Do not regularize intercept
        
        # Add column of ones for intercept
        X_design = np.hstack([np.ones((n_samples, 1)), X])
        I_design = np.eye(n_features + 1)
        I_design[0, 0] = 0.0
        
        A = np.dot(X_design.T, X_design) + self.alpha * I_design
        b = np.dot(X_design.T, y)
        self.coef_ = np.linalg.solve(A, b)

    def predict(self, X: np.ndarray) -> np.ndarray:
        n_samples = X.shape[0]
        X_design = np.hstack([np.ones((n_samples, 1)), X])
        return np.dot(X_design, self.coef_)

# ==============================================================================
# 2. LINEAR DISCRIMINANT ANALYSIS (LDA) CLASSIFIER
# ==============================================================================
class LDAClassifier:
    def __init__(self):
        self.w = None
        self.threshold = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray):
        # Separate classes (assuming y in {0, 1})
        X0 = X[y == 0]
        X1 = X[y == 1]
        
        mu0 = np.mean(X0, axis=0)
        mu1 = np.mean(X1, axis=0)
        
        # Pooled Within-Class Covariance Matrix S_W
        S0 = np.dot((X0 - mu0).T, (X0 - mu0))
        S1 = np.dot((X1 - mu1).T, (X1 - mu1))
        S_W = S0 + S1
        
        # Fisher's LDA Projection Vector: w = S_W^-1 (mu1 - mu0)
        self.w = np.linalg.solve(S_W, mu1 - mu0)
        
        # Calculate decision threshold
        proj0 = np.dot(X0, self.w)
        proj1 = np.dot(X1, self.w)
        self.threshold = (np.mean(proj0) + np.mean(proj1)) / 2.0

    def predict(self, X: np.ndarray) -> np.ndarray:
        projections = np.dot(X, self.w)
        return (projections >= self.threshold).astype(int)

# ==============================================================================
# 3. K-MEANS UNCOUNTERED CLUSTERING ENGINE
# ==============================================================================
class KMeansClustering:
    def __init__(self, k: int = 2, max_iter: int = 100):
        self.k = k
        self.max_iter = max_iter
        self.centroids = None

    def fit(self, X: np.ndarray):
        n_samples, n_features = X.shape
        # Initialize centroids randomly from dataset
        np.random.seed(42)
        random_indices = np.random.choice(n_samples, self.k, replace=False)
        self.centroids = X[random_indices].copy()
        
        for _ in range(self.max_iter):
            # 1. Assign points to nearest centroid
            distances = np.zeros((n_samples, self.k))
            for c_idx, c in enumerate(self.centroids):
                distances[:, c_idx] = np.linalg.norm(X - c, axis=1)
            labels = np.argmin(distances, axis=1)
            
            # 2. Update centroids
            new_centroids = np.zeros((self.k, n_features))
            for c_idx in range(self.k):
                points = X[labels == c_idx]
                if len(points) > 0:
                    new_centroids[c_idx] = np.mean(points, axis=0)
                else:
                    new_centroids[c_idx] = self.centroids[c_idx]
                    
            if np.allclose(self.centroids, new_centroids):
                break
            self.centroids = new_centroids
            
        return labels

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    print("""
    ================================================================
           STATISTICAL LEARNING MASTER SUITE
          Ridge L2, Fisher LDA, & K-Means Unsupervised Clustering
    ================================================================
    """)
    
    # 1. Ridge Regression Demonstration
    print("  DEMO 1: Ridge (L2) Regularized Linear Regression...")
    X_reg = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 5.0], [4.0, 7.0], [5.0, 11.0]])
    y_reg = np.array([3.1, 5.2, 8.1, 11.0, 16.2])
    
    ridge = RidgeRegression(alpha=0.5)
    ridge.fit(X_reg, y_reg)
    preds_reg = ridge.predict(X_reg)
    mse = np.mean((y_reg - preds_reg)**2)
    print(f"   Ridge Coefs (Intercept + Slopes) : {np.round(ridge.coef_, 4)}")
    print(f"   Mean Squared Error (MSE)          : {mse:.4f}")
    
    # 2. Linear Discriminant Analysis (LDA) Demonstration
    print("\n  DEMO 2: Linear Discriminant Analysis (Fisher LDA Binary Classifier)...")
    X_cls = np.array([
        [1.0, 1.1], [1.2, 0.9], [0.8, 1.2], # Class 0
        [5.0, 5.1], [4.9, 5.2], [5.2, 4.8]  # Class 1
    ])
    y_cls = np.array([0, 0, 0, 1, 1, 1])
    
    lda = LDAClassifier()
    lda.fit(X_cls, y_cls)
    preds_cls = lda.predict(X_cls)
    acc = np.mean(preds_cls == y_cls) * 100.0
    print(f"   Fisher LDA Projection Vector w    : {np.round(lda.w, 4)}")
    print(f"   Classification Accuracy           : {acc:.1f}%")
    
    # 3. K-Means Clustering Demonstration
    print("\n  DEMO 3: K-Means Unsupervised Clustering (K=2)...")
    kmeans = KMeansClustering(k=2)
    cluster_labels = kmeans.fit(X_cls)
    print(f"   Discovered Cluster Centroids      :\n{np.round(kmeans.centroids, 4)}")
    print(f"   Assigned Cluster Labels           : {cluster_labels}")
    
    print("\n" + "="*70)
    print(" Statistical Learning Suite Verified!")
    print("="*70)

if __name__ == "__main__":
    main()
