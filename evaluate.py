# Import Flask app and model_search function
from app import app, model_search

# Test queries and expected relevant article IDs
test_queries = [
    ("runcorn election", {15, 90, 252}),
    ("local elections 2025", {179, 329, 254}),
    ("labour party politics", {13, 88, 177, 327}),
]

# Initialize lists to store precision, recall, and F1 scores
precision_list = []
recall_list = []
f1_list = []

# Loop through each query to calculate evaluation metrics
for query, relevant_ids in test_queries:
    # Create an application context for running the Flask code outside a request context
    with app.app_context():
        # Step 1: Call model_search function to retrieve article IDs
        retrieved_ids = model_search(query)
        
    # Step 2: Calculate true positives
    true_positives = len(relevant_ids.intersection(retrieved_ids))
    
    # Step 3: Calculate precision, recall
    precision = true_positives / len(retrieved_ids) if retrieved_ids else 0
    recall = true_positives / len(relevant_ids) if relevant_ids else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
    
    # Append results to respective lists
    precision_list.append(precision)
    recall_list.append(recall)
    f1_list.append(f1)

# Step 4: Calculate Macro-average for precision, recall, and F1 score
macro_precision = sum(precision_list) / len(test_queries)
macro_recall = sum(recall_list) / len(test_queries)
macro_f1 = sum(f1_list) / len(test_queries)

# Print out the evaluation results
print(f"Macro Precision: {macro_precision:.2f}")
print(f"Macro Recall: {macro_recall:.2f}")
print(f"Macro F1 Score: {macro_f1:.2f}")
