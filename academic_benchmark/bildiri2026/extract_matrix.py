#!/usr/bin/env python3
"""Extract time matrix from Veri.xlsx and save as JSON.

Excel structure:
  Row 0: metadata / coordinates
  Row 1: column labels
  Row 2: destinations (D.Kampus, Sw1, Sw2, ...)
  Row 3+: source rows with numeric values
"""

import pandas as pd
import json
import numpy as np

# Read without headers
df = pd.read_excel('data/Veri.xlsx', header=None)

# Target labels from Row 2, columns 2 onwards
target_labels = df.iloc[2, 2:].tolist()
print("Target labels (destinations):")
for i, lbl in enumerate(target_labels):
    print(f"  {i}: {lbl}")

# Numeric data from Row 3+, columns 2+
numeric_data = df.iloc[3:, 2:].apply(pd.to_numeric, errors='coerce')
print(f"\nNumeric data shape: {numeric_data.shape}")
print(f"NaN count: {numeric_data.isna().sum().sum()}")
print(f"Is square? {numeric_data.shape[0] == numeric_data.shape[1]}")

# Verify matrix is square
assert numeric_data.shape[0] == numeric_data.shape[1], "Matrix must be square"
assert numeric_data.isna().sum().sum() == 0, "Matrix contains NaN values"

# Convert to list
matrix = numeric_data.values.tolist()

# Save as JSON
output = {
    "locations": target_labels,
    "time_matrix": matrix,
    "units": "minutes",
    "n_locations": len(target_labels),
    "depot_index": 0,
    "description": "Travel times between 29 locations (D.Kampus + Sw1-Sw9 + So1-So19)"
}

with open('data/student_matrix.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✓ Saved to data/student_matrix.json")
print(f"  Matrix size: {len(matrix)}x{len(matrix[0])}")
print(f"\nFirst 5x5:")
for i in range(5):
    print(f"  {matrix[i][:5]}")

# Quick check - symmetric?
m = np.array(matrix)
asymm_count = np.sum(m != m.T)
print(f"\nAsymmetric entries: {asymm_count}")
if asymm_count > 0:
    print("  Note: Time matrix is asymmetric (directional travel times)")
