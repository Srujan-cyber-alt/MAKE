#!/bin/bash
# MAKE Foundation 5B — GPU Node Setup Script
# Run this on any GPU node with Python 3.10+ to prepare for training/inference.
# Usage: bash production/setup_gpu.sh

set -e

echo "=== MAKE Foundation 5B GPU Setup ==="

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install dependencies
pip install numpy pillow

# Verify installation
python3 -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPUs: {torch.cuda.device_count()}')"

# Create output directories
mkdir -p outputs dataset

echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. python production/dataset.py --source pixabay --max-clips 1000 --output ./dataset"
echo "  2. python production/train.py --config production/configs/production_5b.json"
echo "  3. python production/inference.py --checkpoint outputs/final_model.pt"
