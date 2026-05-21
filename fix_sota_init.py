import re

with open("optimizer_api/strategies/sota_common/__init__.py", "r", encoding="utf-8") as f:
    text = f.read()

# Remove imports for e2bso, paoea, r2dma
text = re.sub(r'from \.e2bso import E2BSO, E2BSOConfig, E2BSOResult\s*\n', '', text)
text = re.sub(r'from \.r2dma import R2DMA, R2DMAConfig, R2DMAResult\s*\n', '', text)
text = re.sub(r'from \.paoea import PAOEA, PAOEAConfig, PAOEAResult\s*\n', '', text)

# Remove from __all__
text = re.sub(r'\s*"E2BSO",\s*"E2BSOConfig",\s*"E2BSOResult",\s*\n', '\n', text)
text = re.sub(r'\s*"R2DMA",\s*"R2DMAConfig",\s*"R2DMAResult",\s*\n', '\n', text)
text = re.sub(r'\s*"PAOEA",\s*"PAOEAConfig",\s*"PAOEAResult",\s*\n', '\n', text)

with open("optimizer_api/strategies/sota_common/__init__.py", "w", encoding="utf-8") as f:
    f.write(text)
