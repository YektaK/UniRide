import requests
import base64
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns

def generate_mermaid_image(mermaid_code, output_filename):
    try:
        # Base64 encode the string
        encoded_string = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        
        # Build the mermaid.ink URL
        url = f"https://mermaid.ink/img/{encoded_string}?bgColor=ffffff"
        
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Successfully generated {output_filename}")
        else:
            print(f"Failed to generate {output_filename}, status code: {response.status_code}")
    except Exception as e:
        print(f"Exception generating {output_filename}: {str(e)}")

# 1. System Architecture Diagram
arch_code = """graph TD
    A[Admin Dashboard - Next.js] -->|Uploads Excel Schedule| B(Data Processing Service)
    B --> C{Supabase Database}
    C -->|Triggers Routing| D[MATLAB Optimization Engine]
    D -->|K-Means Clustering| E[Sub-Cluster Generation]
    E -->|VRP/TSP Solver| F[Route Optimization]
    F -->|Optimal Routes & ETAs| C
    C -->|Assigns Vehicles| G[Driver Dashboard - Next.js]
"""
generate_mermaid_image(arch_code, "Fig1_Architecture.jpg")

# 2. Flowchart
flow_code = """flowchart TD
    Start([Start]) --> Init[/Initialize Data, Capacities, Max Time = 180m/]
    Init --> GetSlots[/Extract Time Slots/]
    GetSlots --> SetCurrent[Set Current_Slot = Latest Time Slot]
    SetCurrent --> CheckEnd{Current_Slot == First?}
    
    CheckEnd -- Yes --> Finish([End])
    CheckEnd -- No --> Filter[Filter Students by Current_Slot]
    Filter --> Cluster[Cluster Students Geographically]
    Cluster --> InitBus[Determine Initial Bus Count K]
    
    InitBus --> LoopStart{For each K}
    LoopStart -- Done --> NextSlot[Move to Previous Time Slot]
    NextSlot --> CheckEnd
    
    LoopStart -- Next k --> OptRoute[Optimize Route k: Depot -> Cluster -> Depot]
    OptRoute --> CalcTime[Calculate Trip_Time for Route k]
    CalcTime --> CheckTime{Trip_Time > 180m?}
    
    CheckTime -- Yes --> IncBus[K = K + 1]
    IncBus --> Recluster[Re-cluster Data]
    Recluster --> InitBus
    
    CheckTime -- No --> SaveRoute[Save Valid Route k]
    SaveRoute --> LoopStart
"""
generate_mermaid_image(flow_code, "Fig2_Flowchart.jpg")

# 3. Conceptual Route
route_code = """graph LR
    Depot((Depot<br>D.Kampus))
    Sw1(Node Sw1)
    Sw2(Node Sw2)
    Sw7(Node Sw7)
    Sw6(Node Sw6)
    
    Depot ==>|40 min| Sw1
    Sw1 ==>|34 min| Sw2
    Sw2 ==>|4 min| Sw7
    Sw7 ==>|13 min| Sw6
    Sw6 ==>|22 min| Depot
    
    style Depot fill:#f9f,stroke:#333,stroke-width:2px
    style Sw1 fill:#bbf,stroke:#333,stroke-width:2px
    style Sw2 fill:#bbf,stroke:#333,stroke-width:2px
    style Sw7 fill:#bbf,stroke:#333,stroke-width:2px
    style Sw6 fill:#bbf,stroke:#333,stroke-width:2px
"""
generate_mermaid_image(route_code, "Fig3a_ConceptualRoute.jpg")

# Generate Performance Bar Charts using Matplotlib
def generate_bar_charts():
    algorithms = ["Nearest Neighbor", "MATLAB TSP", "Google OR-Tools"]
    
    # Chart 1: Average Route Time
    route_times = [142, 118, 115]
    
    plt.figure(figsize=(8, 5))
    sns.set_style("whitegrid")
    ax1 = sns.barplot(x=algorithms, y=route_times, palette="Blues_d")
    plt.title("Expected Route Time Comparison", fontsize=14, fontweight="bold")
    plt.ylabel("Average Route Time (minutes)", fontsize=12)
    plt.ylim(100, 150)
    for p in ax1.patches:
        ax1.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom', fontsize=12, fontweight='bold', color='black', xytext=(0, 5), textcoords='offset points')
    plt.tight_layout()
    plt.savefig("Fig4a_RouteTimeComparison.jpg", dpi=300)
    plt.close()

    # Chart 2: Algorithm Execution Time
    exec_times = [0.05, 12.5, 2.1]
    
    plt.figure(figsize=(8, 5))
    ax2 = sns.barplot(x=algorithms, y=exec_times, palette="Reds_d")
    plt.title("Algorithm Execution Time Comparison", fontsize=14, fontweight="bold")
    plt.ylabel("Execution Time (seconds)", fontsize=12)
    plt.ylim(0, 15)
    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.2f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom', fontsize=12, fontweight='bold', color='black', xytext=(0, 5), textcoords='offset points')
    plt.tight_layout()
    plt.savefig("Fig4b_ExecutionTimeComparison.jpg", dpi=300)
    plt.close()
    print("Successfully generated Bar Charts (Fig4a and Fig4b)")

try:
    generate_bar_charts()
except Exception as e:
    print(f"Failed to generate bar charts: {e}")

print("All image generation scripts executed.")
