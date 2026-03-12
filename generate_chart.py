import matplotlib.pyplot as plt
import numpy as np

# Data for the bar chart
labels = ['Nearest Neighbor', 'MATLAB TSP', 'Google OR-Tools VRP']
route_times = [142, 118, 115] # Average Route Time (minutes)
exec_times = [0.05, 12.5, 2.1] # Algorithm Execution Time (seconds)

x = np.arange(len(labels))
width = 0.35

fig, ax1 = plt.subplots(figsize=(8, 5))

# Plot Route Time on primary y-axis
rects1 = ax1.bar(x - width/2, route_times, width, label='Avg Route Time (min)', color='steelblue')
ax1.set_ylabel('Average Route Time (minutes)', color='steelblue', fontweight='bold')
ax1.tick_params(axis='y', labelcolor='steelblue')

# Plot Execution Time on secondary y-axis
ax2 = ax1.twinx()
rects2 = ax2.bar(x + width/2, exec_times, width, label='Execution Time (sec)', color='darkorange')
ax2.set_ylabel('Execution Time (seconds)', color='darkorange', fontweight='bold')
ax2.tick_params(axis='y', labelcolor='darkorange')

# Formatting
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontweight='bold')
ax1.set_title('Performance Comparison of Routing Algorithms', fontweight='bold')

# Legends
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.tight_layout()
plt.savefig('c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/algorithm_comparison.png', dpi=300)
print('Chart generated successfully.')
