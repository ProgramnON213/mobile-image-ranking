import os
import shutil
import pickle
from sklearn.cluster import DBSCAN

# --- Configuration (Tweak these variables!) ---
INPUT_DIR = 'danbooru/remielle_dan'
OUTPUT_DIR = 'danbooru/remielle_dan_output_batches'
DATA_FILE = 'image_data.pkl'

# DBSCAN Parameters
# eps: Distance threshold. Lower = stricter matches (e.g., 0.05). Higher = looser matches (e.g., 0.2)
EPS = 0.15 
# min_samples: Minimum number of similar images needed to form a batch
MIN_SAMPLES = 2

def run_clustering():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run the extraction script first.")
        return

    print("Loading image embeddings...")
    with open(DATA_FILE, 'rb') as f:
        data = pickle.load(f)
        
    filenames = data['filenames']
    vectors = data['vectors']

    print(f"Running DBSCAN (eps={EPS}, min_samples={MIN_SAMPLES})...")
    # Using 'cosine' metric because we normalized the vectors in the previous script
    cluster_model = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric='cosine')
    labels = cluster_model.fit_predict(vectors)

    print("Organizing files into batches...")
    
    # Create the main output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    outliers_dir = os.path.join(OUTPUT_DIR, 'outliers')
    os.makedirs(outliers_dir, exist_ok=True)

    # Dictionary to keep track of how many files are in each batch for the summary printout
    batch_counts = {'outliers': 0}

    for filename, label in zip(filenames, labels):
        src_path = os.path.join(INPUT_DIR, filename)
        
        # Label -1 means DBSCAN flagged it as an outlier (no similar images found)
        if label == -1:
            dest_dir = outliers_dir
            batch_counts['outliers'] += 1
        else:
            dest_dir = os.path.join(OUTPUT_DIR, f'batch_{label}')
            os.makedirs(dest_dir, exist_ok=True)
            batch_counts[label] = batch_counts.get(label, 0) + 1

        dest_path = os.path.join(dest_dir, filename)
        
        # Copy the file to its new batch folder
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            print(f"Could not copy {filename}: {e}")

    # Print a summary of the results
    print("\n--- Clustering Summary ---")
    total_clusters = len([k for k in batch_counts.keys() if k != 'outliers'])
    print(f"Total Batches Found: {total_clusters}")
    
    for batch_id, count in sorted(batch_counts.items(), key=lambda x: str(x[0])):
        if batch_id == 'outliers':
            print(f"- Outliers: {count} images")
        else:
            print(f"- Batch {batch_id}: {count} images")

if __name__ == '__main__':
    # It is usually best to clear out the old batch folders before a fresh run
    if os.path.exists(OUTPUT_DIR):
        print(f"Cleaning up previous output directory: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
        
    run_clustering()