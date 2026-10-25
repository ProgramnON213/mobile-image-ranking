# ADR-0002: Standardize on PyTorch and Retire TensorFlow

## Status
Accepted

## Date
2026-10-25

## Context
Previously, this workspace maintained two competing deep learning ecosystems in parallel:
1. **PyTorch + Torchvision + Transformers**: Used by [pickWallpaper.py](file:///d:/Download/Gallery-dl/gallery-dl/pickWallpaper.py) and [pickWallpaper_ui.py](file:///d:/Download/Gallery-dl/gallery-dl/pickWallpaper_ui.py) for OpenAI CLIP zero-shot ranking, smart sliding aspect-ratio cropping, and aesthetic scoring.
2. **TensorFlow + Keras**: Used solely by [imageToVector.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector.py) to load `MobileNetV2` for 1280-dimensional feature vector extraction.

This dual-framework architecture caused significant operational issues:
- **Severe Disk Bloat:** Installing TensorFlow, Keras, TensorBoard, and their associated CUDA/cuDNN artifacts consumed ~4 GB of redundant disk space.
- **Startup Latency:** TensorFlow's CUDA runtime and XLA JIT initialization introduced a 3–5 second delay on every script execution before processing a single image.
- **Dependency Conflicts:** Constrained versions of NumPy, typing extensions, and protobuf due to conflicting TensorFlow and PyTorch version requirements.
- **Code Duplication:** Scripts like `imageToVector1.py` existed as near-identical duplicates of `imageToVector.py` solely for incremental caching tweaks.

## Decision
Retire TensorFlow and Keras entirely from the workspace and standardize all deep learning tasks on **PyTorch**:
1. **Migrate [imageToVector.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector.py) to `torchvision.models.mobilenet_v2`:**
   - Extract features using `MobileNet_V2_Weights.DEFAULT` with `model.classifier = torch.nn.Identity()`, preserving the exact 1280-dimensional feature representations.
   - Utilize native PyTorch `torch.nn.functional.normalize(..., p=2, dim=1)` for L2 unit-norm embeddings.
   - Enable automatic hardware acceleration (`device = 'cuda' if torch.cuda.is_available() else 'cpu'`).
   - Implement batched tensor inference (`batch_size=32`) via standard `PIL.Image` loaders.
2. **Standardize Serialization on Compressed NumPy (`.npz`):**
   - Save embeddings via `np.savez_compressed(output_file, filenames=..., vectors=...)` to eliminate arbitrary bytecode execution risks associated with unpickling.
   - Support backwards-compatible loading of existing `.pkl` caches using safe PyTorch deserialization (`weights_only=True`).
3. **Remove TensorFlow from Dependencies:**
   - Remove `tensorflow>=2.12.0` from [requirements.txt](file:///d:/Download/Gallery-dl/requirements.txt).
   - Uninstall `tensorflow` and `keras` from the active virtual environment.
4. **Consolidate Redundant Scripts:**
   - Consolidate incremental caching directly into [imageToVector.py](file:///d:/Download/Gallery-dl/gallery-dl/imageToVector.py) and delete the redundant `imageToVector1.py`.

## Alternatives Considered

### 1. Keep TensorFlow Alongside PyTorch
- **Pros:** No code changes required to `imageToVector.py`.
- **Cons:** Keeps ~4 GB of bloat in developer environments, slows down CI/testing, and perpetuates two incompatible neural network stacks.
- **Rejected:** MobileNetV2 is natively available in `torchvision` with pre-trained ImageNet weights; maintaining TensorFlow for a single model is unwarranted.

### 2. Migrate to ONNX Runtime
- **Pros:** Fast inference engine, small runtime footprint.
- **Cons:** PyTorch is already an unavoidable dependency for CLIP in `pickWallpaper.py`. Adding ONNX Runtime would introduce yet another framework without removing PyTorch.
- **Rejected:** PyTorch is already available, CUDA-optimized, and sufficient for all tasks.

### 3. Replace MobileNetV2 with CLIP ViT Embeddings for Clustering
- **Pros:** Single model architecture across wallpaper ranking and clustering.
- **Cons:** CLIP ViT models are significantly heavier (~350MB–1GB weights vs ~14MB for MobileNetV2) and produce 512-dim or 768-dim embeddings, which would invalidate previously cached embeddings in [clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py).
- **Rejected:** Retaining MobileNetV2 in PyTorch preserves 100% downstream compatibility with existing clustering thresholds (`eps=0.15`).

## Consequences
- **Zero TensorFlow Dependencies:** Complete elimination of `tensorflow` and `keras` from [requirements.txt](file:///d:/Download/Gallery-dl/requirements.txt) and virtual environments.
- **Reclaimed Disk Space:** ~4 GB of disk space saved per environment.
- **Instant Script Startup:** Eliminates TensorFlow CUDA initialization delay; feature extraction starts immediately.
- **Consistent Vector Output:** Generates identical 1280-dimensional L2-normalized feature vectors compatible with [clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py).
- **Single Hardware Pipeline:** Both wallpaper scoring and clustering share the same PyTorch CUDA execution pipeline.
