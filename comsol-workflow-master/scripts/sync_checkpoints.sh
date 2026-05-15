# Legacy Linux helper. This script is retained for cluster usage only.
rsync -av \
  --exclude='*.mph' \
  --exclude='*.txt' \
  --exclude='eigenmodes/' \
  /cluster/scratch/jiayli/workspaces/param_sweep_pairs/ \
  /cluster/home/jiayli/projects/comsol-workflow/checkpoints/pairs/

du -sh /cluster/home/jiayli/projects/comsol-workflow/checkpoints/pairs
