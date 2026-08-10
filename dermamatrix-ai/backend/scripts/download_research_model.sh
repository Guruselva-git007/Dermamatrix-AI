#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$script_dir/models"
curl -L --fail --progress-bar \
  -o "$script_dir/models/ham10000_resnet34_research.ptw" \
  "https://github.com/ptschandl/dermatoscopy_resnet34_nmed_2020/raw/main/model_last_epoch_34_torchvision0_3_state.ptw"
echo "Research weight downloaded. It is for dermatoscopic lesion research only, never medical advice."
