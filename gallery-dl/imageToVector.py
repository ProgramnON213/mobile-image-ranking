import os
import pickle
import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.preprocessing import normalize

# --- Configuration Defaults ---
INPUT_DIR_DEFAULT = 'danbooru/remielle_dan'
OUTPUT_DATA_FILE_DEFAULT = 'image_data.pkl'

def extract_features(input_dir, output_data_file):
    print("Loading pre-trained MobileNetV2 model...")
    # include_top=False removes the final classification layer, leaving the raw embedding vectors
    # pooling='avg' collapses the spatial dimensions into a single 1D vector per image
    model = MobileNetV2(weights='imagenet', include_top=False, pooling='avg')
    
    filenames = []
    feature_list = []
    
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    
    print(f"Scanning '{input_dir}' for images...")
    for filename in os.listdir(input_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_extensions:
            continue
            
        filepath = os.path.join(input_dir, filename)
        
        try:
            # MobileNetV2 requires images to be exactly 224x224 pixels
            img = image.load_img(filepath, target_size=(224, 224))
            img_data = image.img_to_array(img)
            img_data = np.expand_dims(img_data, axis=0)
            img_data = preprocess_input(img_data)
            
            # Extract the vector embedding
            embedding = model.predict(img_data, verbose=0)
            
            filenames.append(filename)
            feature_list.append(embedding[0])
            print(f"Processed: {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    if not feature_list:
        print("No images found or processed successfully.")
        return

    print("\nNormalizing feature vectors...")
    # Normalizing is required so we can accurately use Cosine distance in DBSCAN
    feature_vectors = np.array(feature_list)
    normalized_vectors = normalize(feature_vectors)

    print(f"Saving data to {output_data_file}...")
    with open(output_data_file, 'wb') as f:
        pickle.dump({'filenames': filenames, 'vectors': normalized_vectors}, f)
        
    print("Extraction complete! You can now run the clustering script.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Extract feature vectors from images using MobileNetV2.")
    parser.add_argument("--input-dir", "-i", default=INPUT_DIR_DEFAULT, help=f"Input directory of images (default: '{INPUT_DIR_DEFAULT}')")
    parser.add_argument("--output-file", "-o", default=OUTPUT_DATA_FILE_DEFAULT, help=f"Output data file (default: '{OUTPUT_DATA_FILE_DEFAULT}')")
    args = parser.parse_args()

    # Ensure input directory exists
    os.makedirs(args.input_dir, exist_ok=True)
    extract_features(args.input_dir, args.output_file)