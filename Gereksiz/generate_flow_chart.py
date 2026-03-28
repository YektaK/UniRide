import requests
import base64

flow_code = """graph TD
    Start([Start]) --> Init["Initialize Data"]
    Init --> GetSlots["Extract Time Slots"]
    GetSlots --> SetCurrent[Set Current_Slot = Latest Time Slot]
    SetCurrent --> CheckEnd{Current_Slot == First?}
    
    CheckEnd -- Yes --> Finish([End])
    CheckEnd -- No --> Filter[Filter Students by Current_Slot]
    Filter --> Cluster[Cluster Students Geographically]
    Cluster --> InitBus[Determine Initial Bus Count K]
    
    InitBus --> LoopStart{For each K}
    LoopStart -- Done --> NextSlot[Move to Previous Time Slot]
    NextSlot --> CheckEnd
    
    LoopStart -- Next k --> OptRoute[Optimize Route k: Depot to Cluster to Depot]
    OptRoute --> CalcTime[Calculate Trip_Time for Route k]
    CalcTime --> CheckTime{Trip_Time > 180m?}
    
    CheckTime -- Yes --> IncBus[K = K + 1]
    IncBus --> Recluster[Re-cluster Data]
    Recluster --> InitBus
    
    CheckTime -- No --> SaveRoute[Save Valid Route k]
    SaveRoute --> LoopStart
"""

encoded = base64.b64encode(flow_code.encode('utf-8')).decode('utf-8')
url = f'https://mermaid.ink/img/{encoded}?bgColor=ffffff'
r = requests.get(url)
if r.status_code == 200:
    with open('c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/Fig2_Flowchart.jpg', 'wb') as f:
        f.write(r.content)
    print('Generated Fig2_Flowchart.jpg successfully')
else:
    print('Failed:', r.status_code)
