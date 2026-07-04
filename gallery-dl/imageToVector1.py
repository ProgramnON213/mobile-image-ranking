import os
import pickle
import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.preprocessing import normalize

# --- Configuration Defaults ---
INPUT_DIR_DEFAULT = 'danbooru/remielle_dan'
OUTPUT_DATA_FILE_DEFAULT = 'image_data.pkl'

def extract_features_incrementally(input_dir, output_data_file):
    existing_filenames = []
    existing_vectors = []
    
    # 1. Load existing memory if it exists
    if os.path.exists(output_data_file):
        print(f"Loading existing data from {output_data_file}...")
        with open(output_data_file, 'rb') as f:
            data = pickle.load(f)
            existing_filenames = data['filenames']
            existing_vectors = data['vectors']
        print(f"Found {len(existing_filenames)} previously processed images. Skipping those...")

    print("Loading pre-trained MobileNetV2 model...")
    model = MobileNetV2(weights='imagenet', include_top=False, pooling='avg')
    
    new_filenames = []
    new_features = []
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    
    print(f"Scanning '{input_dir}' for new images...")
    for filename in os.listdir(input_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_extensions:
            continue
            
        # 2. The Gatekeeper: Skip if already processed
        if filename in existing_filenames:
            continue
            
        filepath = os.path.join(input_dir, filename)
        
        try:
            img = image.load_img(filepath, target_size=(224, 224))
            img_data = image.img_to_array(img)
            img_data = np.expand_dims(img_data, axis=0)
            img_data = preprocess_input(img_data)
            
            embedding = model.predict(img_data, verbose=0)
            
            new_filenames.append(filename)
            new_features.append(embedding[0])
            print(f"Processed New Image: {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # 3. Handle the merge
    if not new_features:
        print("No new images found. Everything is up to date!")
        return

    print("\nNormalizing new feature vectors...")
    new_normalized_vectors = normalize(np.array(new_features))

    # Combine the old data with the new data
    if len(existing_filenames) > 0:
        final_filenames = existing_filenames + new_filenames
        final_vectors = np.vstack((existing_vectors, new_normalized_vectors))
    else:
        final_filenames = new_filenames
        final_vectors = new_normalized_vectors

    print(f"Saving {len(final_filenames)} total vectors to {output_data_file}...")
    with open(output_data_file, 'wb') as f:
        pickle.dump({'filenames': final_filenames, 'vectors': final_vectors}, f)
        
    print("Incremental update complete!")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Incrementally extract feature vectors from images using MobileNetV2.")
    parser.add_argument("--input-dir", "-i", default=INPUT_DIR_DEFAULT, help=f"Input directory of images (default: '{INPUT_DIR_DEFAULT}')")
    parser.add_argument("--output-file", "-o", default=OUTPUT_DATA_FILE_DEFAULT, help=f"Output data file (default: '{OUTPUT_DATA_FILE_DEFAULT}')")
    args = parser.parse_args()

    os.makedirs(args.input_dir, exist_ok=True)
    extract_features_incrementally(args.input_dir, args.output_file)