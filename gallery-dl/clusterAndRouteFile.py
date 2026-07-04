import os
import shutil
import pickle
from sklearn.cluster import DBSCAN

# --- Configuration Defaults ---
INPUT_DIR_DEFAULT = 'danbooru/remielle_dan'
OUTPUT_DIR_DEFAULT = 'danbooru/remielle_dan_output_batches'
DATA_FILE_DEFAULT = 'image_data.pkl'
EPS_DEFAULT = 0.15 
MIN_SAMPLES_DEFAULT = 2

def run_clustering(input_dir, output_dir, data_file, eps, min_samples):
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found. Run the extraction script first.")
        return

    print("Loading image embeddings...")
    with open(data_file, 'rb') as f:
        data = pickle.load(f)
        
    filenames = data['filenames']
    vectors = data['vectors']

    print(f"Running DBSCAN (eps={eps}, min_samples={min_samples})...")
    # Using 'cosine' metric because we normalized the vectors in the previous script
    cluster_model = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = cluster_model.fit_predict(vectors)

    print("Organizing files into batches...")
    
    # Create the main output directory
    os.makedirs(output_dir, exist_ok=True)
    
    outliers_dir = os.path.join(output_dir, 'outliers')
    os.makedirs(outliers_dir, exist_ok=True)

    # Dictionary to keep track of how many files are in each batch for the summary printout
    batch_counts = {'outliers': 0}

    for filename, label in zip(filenames, labels):
        src_path = os.path.join(input_dir, filename)
        
        # Label -1 means DBSCAN flagged it as an outlier (no similar images found)
        if label == -1:
            dest_dir = outliers_dir
            batch_counts['outliers'] += 1
        else:
            dest_dir = os.path.join(output_dir, f'batch_{label}')
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
    import argparse
    parser = argparse.ArgumentParser(description="Organize images into batches using DBSCAN clustering.")
    parser.add_argument("--input-dir", "-i", default=INPUT_DIR_DEFAULT, help=f"Input directory of images (default: '{INPUT_DIR_DEFAULT}')")
    parser.add_argument("--output-dir", "-o", default=OUTPUT_DIR_DEFAULT, help=f"Output directory for batches (default: '{OUTPUT_DIR_DEFAULT}')")
    parser.add_argument("--data-file", "-d", default=DATA_FILE_DEFAULT, help=f"Image data pickle file (default: '{DATA_FILE_DEFAULT}')")
    parser.add_argument("--eps", "-e", type=float, default=EPS_DEFAULT, help=f"DBSCAN epsilon parameter (default: {EPS_DEFAULT})")
    parser.add_argument("--min-samples", "-m", type=int, default=MIN_SAMPLES_DEFAULT, help=f"DBSCAN min_samples parameter (default: {MIN_SAMPLES_DEFAULT})")
    args = parser.parse_args()

    # It is usually best to clear out the old batch folders before a fresh run
    if os.path.exists(args.output_dir):
        print(f"Cleaning up previous output directory: {args.output_dir}")
        shutil.rmtree(args.output_dir)
        
    run_clustering(args.input_dir, args.output_dir, args.data_file, args.eps, args.min_samples)