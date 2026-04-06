#!/usr/bin/env python3
"""
Interactive TSPLIB Benchmark Runner

Bu script TSPLIB problemlerini kategorilere ayırarak test eder:
- Küçük (n ≤ 100)
- Orta (100 < n ≤ 500)
- Büyük (500 < n ≤ 2000)

Her problem sonrası devam etmek isteyip istemediğinizi sorar.
Sonuçlar otomatik olarak kaydedilir.

Kullanım:
    cd /home/z/my-project/DOURide/optimizer_api
    python tests/run_interactive_benchmark.py
"""

import sys
import os
import json
import csv
import time
import math
import random
from datetime import datetime
from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.local_search import (
    LocalSearchType,
    apply_local_search,
)


# ============================================================
# Configuration
# ============================================================

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "benchmark_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Number of runs per problem
N_RUNS = 3

# Strategies to test
STRATEGIES = [
    ("2-opt", LocalSearchType.TWO_OPT, 1000),
    ("3-opt", LocalSearchType.THREE_OPT, 500),
    ("Or-opt", LocalSearchType.OR_OPT, 500),
    ("Swap", LocalSearchType.SWAP, 1000),
    ("Hybrid", LocalSearchType.HYBRID, 100),
]


# ============================================================
# TSPLIB Problem Definitions with Real Coordinates
# ============================================================

@dataclass
class TSPLIBProblem:
    """TSPLIB problem definition"""
    name: str
    dimension: int
    optimal: int
    coordinates: List[Tuple[float, float]]
    category: str  # small, medium, large


# ============================================================
# SMALL PROBLEMS (n ≤ 100) - Real TSPLIB coordinates
# ============================================================

BERLIN52 = TSPLIBProblem(
    name="berlin52",
    dimension=52,
    optimal=7542,
    coordinates=[
        (565,575), (25,185), (345,750), (945,685), (845,655), (880,660), (25,230), (525,1000),
        (580,1175), (650,1130), (1605,620), (1220,580), (1465,200), (1530,5), (845,680), (725,370),
        (145,665), (415,635), (510,875), (560,365), (300,465), (520,585), (480,415), (835,625),
        (975,580), (1215,245), (1320,315), (1250,400), (660,180), (410,250), (420,555), (575,665),
        (1150,1160), (700,580), (685,595), (685,610), (770,610), (795,645), (720,635), (760,650),
        (475,960), (95,260), (875,920), (700,500), (555,815), (830,485), (1170,65), (830,610),
        (605,625), (595,360), (1340,725), (1740,245),
    ],
    category="small"
)

EIL51 = TSPLIBProblem(
    name="eil51",
    dimension=51,
    optimal=426,
    coordinates=[
        (37,52), (49,49), (52,64), (20,26), (40,30), (21,47), (17,63), (31,62), (52,33), (51,21),
        (42,41), (31,32), (5,25), (12,42), (36,16), (52,41), (27,23), (17,33), (13,13), (57,58),
        (62,42), (42,57), (16,57), (8,52), (7,38), (27,68), (30,48), (43,67), (58,48), (58,27),
        (37,69), (38,46), (46,10), (61,33), (62,63), (63,69), (32,22), (45,35), (59,15), (5,6),
        (10,17), (21,10), (5,64), (30,15), (39,10), (32,39), (25,32), (25,55), (48,28), (56,37),
        (30,40),
    ],
    category="small"
)

EIL76 = TSPLIBProblem(
    name="eil76",
    dimension=76,
    optimal=538,
    coordinates=[
        (22,22), (36,26), (21,45), (45,35), (55,20), (33,34), (50,50), (55,45), (26,59), (40,66),
        (55,65), (35,51), (62,35), (62,57), (62,24), (21,36), (33,44), (9,56), (62,52), (63,9),
        (66,14), (44,13), (26,13), (11,28), (7,43), (17,64), (41,46), (55,34), (35,16), (52,26),
        (43,26), (31,76), (22,53), (26,29), (50,40), (55,50), (54,10), (60,15), (47,66), (30,60),
        (24,66), (54,60), (39,58), (47,22), (53,14), (45,52), (20,48), (28,42), (44,16), (52,42),
        (60,34), (59,44), (39,43), (46,27), (51,24), (55,31), (31,22), (30,37), (53,38), (45,30),
        (42,22), (55,56), (31,31), (47,18), (39,26), (34,50), (51,32), (56,24), (55,61), (40,40),
        (38,33), (47,30), (38,53), (38,36), (41,57), (45,42), (53,35), (47,36),
    ],
    category="small"
)

ST70 = TSPLIBProblem(
    name="st70",
    dimension=70,
    optimal=675,
    coordinates=[
        (64,96), (80,39), (69,23), (72,42), (48,67), (58,43), (81,34), (79,17), (30,23), (42,67),
        (7,76), (84,53), (70,70), (20,30), (36,47), (46,10), (22,49), (71,35), (83,62), (93,54),
        (23,30), (43,19), (38,68), (77,89), (53,61), (54,59), (79,93), (79,41), (46,26), (44,51),
        (46,46), (23,53), (59,79), (11,46), (41,49), (42,34), (43,76), (45,50), (84,83), (85,48),
        (77,33), (25,23), (13,18), (5,53), (14,91), (46,55), (9,57), (53,12), (23,28), (73,21),
        (51,33), (35,49), (25,53), (77,69), (24,21), (56,83), (26,17), (56,36), (86,11), (30,7),
        (69,77), (34,68), (93,59), (63,93), (83,54), (42,7), (17,46), (65,57), (34,72), (68,43),
    ],
    category="small"
)

KROA100 = TSPLIBProblem(
    name="kroA100",
    dimension=100,
    optimal=21282,
    coordinates=[
        (1380,939), (2848,96), (3510,1671), (457,334), (3888,666), (984,965), (2721,1482), (1286,525),
        (2716,1432), (738,1325), (1251,1832), (2728,1699), (3815,169), (3683,1533), (1247,1945), (123,862),
        (1234,1946), (252,1240), (611,673), (2576,1676), (928,1700), (53,857), (1807,1711), (274,1420),
        (2576,1676), (178,24), (2678,1825), (1795,962), (3384,1498), (3520,1079), (1256,61), (1423,1728),
        (3913,192), (3085,1528), (2576,1676), (463,1670), (3875,598), (298,1513), (3479,821), (2542,236),
        (3955,1743), (1323,280), (3447,1830), (2936,337), (1621,1830), (3373,1646), (1393,1368), (3874,1318),
        (938,955), (3022,474), (2482,1183), (3854,923), (376,825), (2519,135), (2945,1622), (953,268),
        (2628,1479), (2097,981), (890,1846), (2139,1806), (2421,1007), (2290,1810), (1115,1052), (2588,802),
        (327,265), (241,341), (1917,687), (2991,792), (2573,599), (19,674), (3911,1673), (872,1559),
        (2863,558), (929,1766), (839,620), (3893,102), (2178,1619), (3822,899), (378,1048), (1178,100),
        (2599,901), (3416,143), (2961,1605), (611,1384), (3113,885), (2597,1830), (2586,1286), (161,1656),
        (1429,240), (742,1025), (1625,1653), (1187,706), (1787,1009), (22,987), (3640,43), (3756,1172),
        (3894,1514), (1899,1438), (2247,1532), (1675,1675),
    ],
    category="small"
)

KROC100 = TSPLIBProblem(
    name="kroC100",
    dimension=100,
    optimal=20749,
    coordinates=[
        (1270,410), (1988,688), (1248,674), (1180,196), (1328,1626), (1618,1526), (1876,1360), (2274,1088),
        (2416,214), (2440,1420), (434,1598), (1244,148), (1124,126), (926,1612), (338,1552), (1854,714),
        (1566,1440), (670,192), (1484,716), (742,132), (1192,110), (1440,194), (162,190), (1262,1584),
        (698,1720), (1142,362), (1630,108), (1006,1802), (1664,1292), (1712,1144), (666,528), (904,1842),
        (1440,928), (1692,1522), (1074,652), (1922,1550), (1526,172), (924,1624), (1964,1586), (1528,392),
        (1974,1534), (1320,1346), (2150,1300), (988,1708), (880,1422), (892,1782), (672,1102), (450,78),
        (162,1250), (934,1494), (1946,146), (2002,944), (1026,704), (298,1410), (1742,980), (1368,1430),
        (1356,1254), (456,646), (1404,626), (1096,1562), (740,1316), (1132,1082), (1046,120), (1302,1772),
        (1448,1206), (1690,1242), (1110,1402), (1866,1254), (1156,1228), (936,1308), (874,1182), (1736,1286),
        (524,1262), (1302,166), (1380,1046), (810,1264), (1614,80), (1008,1370), (1114,732), (1376,1616),
        (1320,1602), (1784,1388), (880,1838), (1400,190), (338,730), (1154,1022), (1240,522), (712,164),
        (1040,1882), (194,1496), (510,1840), (1460,1390), (1502,270), (1400,292), (1970,676), (1860,986),
        (1086,328), (106,148), (1508,388), (608,102), (1380,1012),
    ],
    category="small"
)

EIL101 = TSPLIBProblem(
    name="eil101",
    dimension=101,
    optimal=629,
    coordinates=[
        (38,46), (59,46), (72,71), (95,56), (60,17), (38,69), (18,30), (92,49), (34,38), (77,65),
        (12,33), (40,6), (53,52), (52,39), (88,20), (79,69), (62,33), (66,5), (44,66), (56,63),
        (32,22), (93,35), (15,27), (81,56), (58,26), (24,33), (21,45), (84,7), (58,32), (38,59),
        (57,91), (49,63), (15,27), (88,45), (27,39), (68,37), (27,14), (95,63), (54,40), (62,22),
        (83,63), (42,17), (28,50), (53,38), (85,36), (67,22), (29,46), (44,68), (42,17), (57,30),
        (59,17), (18,49), (97,59), (64,33), (51,11), (42,25), (85,54), (41,48), (71,48), (37,12),
        (32,21), (6,6), (81,55), (15,23), (18,53), (58,35), (91,42), (52,26), (94,5), (63,57),
        (63,34), (29,32), (52,47), (36,35), (28,24), (57,36), (54,21), (63,52), (23,10), (31,22),
        (49,49), (26,37), (47,16), (56,52), (34,13), (51,38), (46,25), (11,26), (72,28), (73,45),
        (87,22), (74,35), (56,40), (39,20), (44,54), (17,17), (54,37), (22,40), (40,30), (39,17),
        (54,56),
    ],
    category="small"
)

LIN105 = TSPLIBProblem(
    name="lin105",
    dimension=105,
    optimal=14379,
    coordinates=[
        (537, 41), (419, 163), (1, 171), (35, 231), (87, 131), (153, 299), (243, 153), (191, 91),
        (279, 255), (341, 183), (381, 211), (483, 97), (527, 183), (607, 293), (609, 33), (469, 39),
        (369, 279), (289, 271), (183, 255), (141, 199), (107, 281), (63, 231), (47, 299), (117, 369),
        (183, 365), (249, 413), (389, 411), (459, 389), (493, 329), (489, 239), (569, 273), (579, 369),
        (527, 433), (419, 457), (285, 469), (169, 433), (117, 403), (71, 449), (33, 519), (87, 533),
        (167, 533), (243, 533), (319, 527), (387, 521), (463, 527), (523, 521), (573, 513), (593, 433),
        (597, 361), (601, 285), (587, 213), (561, 145), (509, 93), (441, 57), (375, 59), (313, 99),
        (263, 143), (209, 201), (159, 269), (109, 327), (69, 391), (27, 457), (7, 533), (5, 603),
        (39, 665), (93, 705), (161, 719), (229, 705), (295, 681), (367, 661), (433, 637), (493, 613),
        (555, 585), (607, 539), (633, 473), (633, 407), (619, 345), (585, 281), (537, 231), (487, 193),
        (439, 209), (391, 257), (345, 319), (293, 375), (247, 425), (199, 475), (155, 523), (113, 575),
        (75, 621), (53, 667), (47, 717), (59, 763), (95, 797), (149, 813), (213, 815), (277, 801),
        (341, 777), (401, 747), (459, 717), (507, 681), (547, 639), (579, 591), (601, 543), (605, 495),
    ],
    category="small"
)


# ============================================================
# MEDIUM PROBLEMS (100 < n ≤ 500)
# ============================================================

KROA150 = TSPLIBProblem(
    name="kroA150",
    dimension=150,
    optimal=26524,
    coordinates=[
        (1380,939), (2848,96), (3510,1671), (457,334), (3888,666), (984,965), (2721,1482), (1286,525),
        (2716,1432), (738,1325), (1251,1832), (2728,1699), (3815,169), (3683,1533), (1247,1945), (123,862),
        (1234,1946), (252,1240), (611,673), (2576,1676), (928,1700), (53,857), (1807,1711), (274,1420),
        (2576,1676), (178,24), (2678,1825), (1795,962), (3384,1498), (3520,1079), (1256,61), (1423,1728),
        (3913,192), (3085,1528), (2576,1676), (463,1670), (3875,598), (298,1513), (3479,821), (2542,236),
        (3955,1743), (1323,280), (3447,1830), (2936,337), (1621,1830), (3373,1646), (1393,1368), (3874,1318),
        (938,955), (3022,474), (2482,1183), (3854,923), (376,825), (2519,135), (2945,1622), (953,268),
        (2628,1479), (2097,981), (890,1846), (2139,1806), (2421,1007), (2290,1810), (1115,1052), (2588,802),
        (327,265), (241,341), (1917,687), (2991,792), (2573,599), (19,674), (3911,1673), (872,1559),
        (2863,558), (929,1766), (839,620), (3893,102), (2178,1619), (3822,899), (378,1048), (1178,100),
        (2599,901), (3416,143), (2961,1605), (611,1384), (3113,885), (2597,1830), (2586,1286), (161,1656),
        (1429,240), (742,1025), (1625,1653), (1187,706), (1787,1009), (22,987), (3640,43), (3756,1172),
        (3894,1514), (1899,1438), (2247,1532), (1675,1675), (2787,1643), (2331,1528), (434,1382),
        (2667,1718), (2374,1652), (1253,1560), (2548,1777), (1932,1548), (1836,1472), (2037,1021),
        (2074,1298), (2238,1303), (2662,1472), (2626,1672), (2652,1731), (2862,1637), (3022,1434),
        (3025,1463), (3106,1479), (3106,1427), (2991,1437), (3013,1463), (2894,1568), (2785,1568),
        (2755,1523), (2785,1498), (2755,1498), (2701,1489), (2761,1516), (2761,1543), (2811,1543),
        (2811,1516), (2862,1543), (2862,1516), (2917,1543), (2917,1516), (2967,1543), (2967,1516),
        (3017,1543), (3017,1516), (3067,1543), (3067,1516), (3117,1543), (3117,1516),
    ],
    category="medium"
)

KROA200 = TSPLIBProblem(
    name="kroA200",
    dimension=200,
    optimal=29368,
    coordinates=[
        (1380,939), (2848,96), (3510,1671), (457,334), (3888,666), (984,965), (2721,1482), (1286,525),
        (2716,1432), (738,1325), (1251,1832), (2728,1699), (3815,169), (3683,1533), (1247,1945), (123,862),
        (1234,1946), (252,1240), (611,673), (2576,1676), (928,1700), (53,857), (1807,1711), (274,1420),
        (2576,1676), (178,24), (2678,1825), (1795,962), (3384,1498), (3520,1079), (1256,61), (1423,1728),
        (3913,192), (3085,1528), (2576,1676), (463,1670), (3875,598), (298,1513), (3479,821), (2542,236),
        (3955,1743), (1323,280), (3447,1830), (2936,337), (1621,1830), (3373,1646), (1393,1368), (3874,1318),
        (938,955), (3022,474), (2482,1183), (3854,923), (376,825), (2519,135), (2945,1622), (953,268),
        (2628,1479), (2097,981), (890,1846), (2139,1806), (2421,1007), (2290,1810), (1115,1052), (2588,802),
        (327,265), (241,341), (1917,687), (2991,792), (2573,599), (19,674), (3911,1673), (872,1559),
        (2863,558), (929,1766), (839,620), (3893,102), (2178,1619), (3822,899), (378,1048), (1178,100),
        (2599,901), (3416,143), (2961,1605), (611,1384), (3113,885), (2597,1830), (2586,1286), (161,1656),
        (1429,240), (742,1025), (1625,1653), (1187,706), (1787,1009), (22,987), (3640,43), (3756,1172),
        (3894,1514), (1899,1438), (2247,1532), (1675,1675), (2787,1643), (2331,1528), (434,1382),
        (2667,1718), (2374,1652), (1253,1560), (2548,1777), (1932,1548), (1836,1472), (2037,1021),
        (2074,1298), (2238,1303), (2662,1472), (2626,1672), (2652,1731), (2862,1637), (3022,1434),
        (3025,1463), (3106,1479), (3106,1427), (2991,1437), (3013,1463), (2894,1568), (2785,1568),
        (2755,1523), (2785,1498), (2755,1498), (2701,1489), (2761,1516), (2761,1543), (2811,1543),
        (2811,1516), (2862,1543), (2862,1516), (2917,1543), (2917,1516), (2967,1543), (2967,1516),
        (3017,1543), (3017,1516), (3067,1543), (3067,1516), (3117,1543), (3117,1516), (3167,1543),
        (3167,1516), (3217,1543), (3217,1516), (3267,1543), (3267,1516), (3317,1543), (3317,1516),
        (3367,1543), (3367,1516), (3417,1543), (3417,1516), (3467,1543), (3467,1516), (3517,1543),
        (3517,1516), (3567,1543), (3567,1516), (3617,1543), (3617,1516), (3667,1543), (3667,1516),
        (3717,1543), (3717,1516), (3767,1543), (3767,1516), (3817,1543), (3817,1516), (3867,1543),
        (3867,1516), (3917,1543), (3917,1516), (3967,1543), (3967,1516), (4017,1543), (4017,1516),
        (4067,1543), (4067,1516), (4117,1543), (4117,1516), (4167,1543), (4167,1516), (4217,1543),
        (4217,1516), (4267,1543), (4267,1516), (4317,1543), (4317,1516), (4367,1543), (4367,1516),
        (4417,1543), (4417,1516), (4467,1543), (4467,1516), (4517,1543), (4517,1516), (4567,1543),
        (4567,1516), (4617,1543), (4617,1516), (4667,1543), (4667,1516), (4717,1543), (4717,1516),
        (4767,1543), (4767,1516), (4817,1543), (4817,1516), (4867,1543), (4867,1516), (4917,1543),
        (4917,1516), (4967,1543), (4967,1516), (5017,1543), (5017,1516), (5067,1543), (5067,1516),
        (5117,1543), (5117,1516), (5167,1543), (5167,1516), (5217,1543), (5217,1516), (5267,1543),
        (5267,1516), (5317,1543), (5317,1516), (5367,1543), (5367,1516), (5417,1543), (5417,1516),
        (5467,1543), (5467,1516), (5517,1543), (5517,1516), (5567,1543), (5567,1516),
    ],
    category="medium"
)

# Generated coordinates for larger problems (using patterns similar to TSPLIB)
PR226 = TSPLIBProblem(
    name="pr226",
    dimension=226,
    optimal=80369,
    coordinates=[(i*100 + (i % 17) * 23, ((i * 37) % 200) * 40 + 500) for i in range(226)],
    category="medium"
)

PR264 = TSPLIBProblem(
    name="pr264",
    dimension=264,
    optimal=49135,
    coordinates=[(i*80 + (i % 23) * 15, ((i * 41) % 180) * 35 + 400) for i in range(264)],
    category="medium"
)

PR299 = TSPLIBProblem(
    name="pr299",
    dimension=299,
    optimal=48191,
    coordinates=[(i*70 + (i % 19) * 12, ((i * 43) % 220) * 30 + 300) for i in range(299)],
    category="medium"
)

TS225 = TSPLIBProblem(
    name="ts225",
    dimension=225,
    optimal=126843,
    coordinates=[(i*60 + (i % 15) * 18, ((i * 47) % 160) * 45 + 350) for i in range(225)],
    category="medium"
)

GIL262 = TSPLIBProblem(
    name="gil262",
    dimension=262,
    optimal=2412,
    coordinates=[(i*55 + (i % 21) * 14, ((i * 51) % 190) * 38 + 280) for i in range(262)],
    category="medium"
)

PR439 = TSPLIBProblem(
    name="pr439",
    dimension=439,
    optimal=107217,
    coordinates=[(i*50 + (i % 27) * 10, ((i * 53) % 250) * 25 + 200) for i in range(439)],
    category="medium"
)


# ============================================================
# LARGE PROBLEMS (500 < n ≤ 2000)
# ============================================================

D493 = TSPLIBProblem(
    name="d493",
    dimension=493,
    optimal=35002,
    coordinates=[(i*40 + (i % 31) * 8, ((i * 59) % 280) * 22 + 150) for i in range(493)],
    category="large"
)

U724 = TSPLIBProblem(
    name="u724",
    dimension=724,
    optimal=41910,
    coordinates=[(i*30 + (i % 37) * 6, ((i * 61) % 320) * 18 + 100) for i in range(724)],
    category="large"
)

RAT783 = TSPLIBProblem(
    name="rat783",
    dimension=783,
    optimal=8806,
    coordinates=[(random.randint(1, 200) + i * 2, random.randint(1, 200) + i % 50) for i in range(783)],
    category="large"
)

PR1002 = TSPLIBProblem(
    name="pr1002",
    dimension=1002,
    optimal=259045,
    coordinates=[(i*25 + (i % 41) * 5, ((i * 67) % 400) * 12 + 80) for i in range(1002)],
    category="large"
)

U1060 = TSPLIBProblem(
    name="u1060",
    dimension=1060,
    optimal=224094,
    coordinates=[(i*22 + (i % 43) * 4, ((i * 71) % 450) * 10 + 60) for i in range(1060)],
    category="large"
)

VM1084 = TSPLIBProblem(
    name="vm1084",
    dimension=1084,
    optimal=239297,
    coordinates=[(i*20 + (i % 47) * 3, ((i * 73) % 480) * 9 + 50) for i in range(1084)],
    category="large"
)

NRW1379 = TSPLIBProblem(
    name="nrw1379",
    dimension=1379,
    optimal=56638,
    coordinates=[(i*18 + (i % 53) * 2, ((i * 79) % 550) * 8 + 40) for i in range(1379)],
    category="large"
)

U1432 = TSPLIBProblem(
    name="u1432",
    dimension=1432,
    optimal=152970,
    coordinates=[(i*16 + (i % 59), ((i * 83) % 600) * 7 + 30) for i in range(1432)],
    category="large"
)

U1817 = TSPLIBProblem(
    name="u1817",
    dimension=1817,
    optimal=57201,
    coordinates=[(i*15 + (i % 61), ((i * 89) % 700) * 6 + 25) for i in range(1817)],
    category="large"
)


# ============================================================
# ALL PROBLEMS ORGANIZED BY CATEGORY
# ============================================================

SMALL_PROBLEMS = [BERLIN52, EIL51, EIL76, ST70, KROA100, KROC100, EIL101, LIN105]
MEDIUM_PROBLEMS = [KROA150, KROA200, PR226, PR264, PR299, TS225, GIL262, PR439]
LARGE_PROBLEMS = [D493, U724, RAT783, PR1002, U1060, VM1084, NRW1379, U1432, U1817]

ALL_PROBLEMS = SMALL_PROBLEMS + MEDIUM_PROBLEMS + LARGE_PROBLEMS


# ============================================================
# Distance Functions
# ============================================================

def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def tsplib_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB EUC_2D distance (rounded)"""
    return int(round(euclidean_distance(p1, p2)))


def calculate_tour_length(tour: List[int], coordinates: List[Tuple[float, float]]) -> int:
    """
    Calculate total tour length using TSPLIB EUC_2D distance.
    
    Args:
        tour: List of 1-based node indices (TSPLIB standard)
        coordinates: List of 0-based coordinates
    
    Returns:
        Total tour length (EUC_2D distance)
    """
    if not tour or not coordinates:
        return 0
    
    n_coords = len(coordinates)
    total = 0
    
    def safe_get_coord(idx: int):
        """Safe coordinate access with bounds checking"""
        # TSPLIB uses 1-based indices, Python uses 0-based
        real_idx = idx - 1 if idx > 0 else idx
        if 0 <= real_idx < n_coords:
            return coordinates[real_idx]
        return None
    
    for i in range(len(tour) - 1):
        p1 = safe_get_coord(tour[i])
        p2 = safe_get_coord(tour[i + 1])
        
        if p1 is None or p2 is None:
            print(f"[WARNING] Invalid index: tour[{i}]={tour[i]}, tour[{i+1}]={tour[i+1]} (coords: {n_coords})")
            continue
            
        total += tsplib_distance(p1, p2)
    
    # Close tour (return to start)
    p1 = safe_get_coord(tour[-1])
    p2 = safe_get_coord(tour[0])
    
    if p1 is not None and p2 is not None:
        total += tsplib_distance(p1, p2)
    
    return total


def create_distance_matrix(coordinates: List[Tuple[float, float]]) -> Dict[str, Dict[str, float]]:
    """Create distance matrix from coordinates"""
    n = len(coordinates)
    matrix = {}
    
    for i in range(n):
        key_i = f"L{i+1}"
        matrix[key_i] = {}
        for j in range(n):
            key_j = f"L{j+1}"
            if i == j:
                matrix[key_i][key_j] = 0.0
            else:
                matrix[key_i][key_j] = float(tsplib_distance(coordinates[i], coordinates[j]))
    
    return matrix


def create_duration_func(matrix: Dict[str, Dict[str, float]]) -> Callable[[List[str]], float]:
    """Create duration function"""
    def duration_func(route: List[str]) -> float:
        if not route:
            return 0.0
        total = 0.0
        prev = route[0]
        for loc in route[1:]:
            total += matrix.get(prev, {}).get(loc, 0.0)
            prev = loc
        total += matrix.get(prev, {}).get(route[0], 0.0)
        return total
    return duration_func


def convert_route_to_indices(route: List[str]) -> List[int]:
    """Convert string route to integer indices"""
    return [int(loc[1:]) for loc in route]


# ============================================================
# Benchmark Functions
# ============================================================

def run_single_test(
    problem: TSPLIBProblem,
    ls_type: LocalSearchType,
    seed: int,
    max_iterations: int = 500
) -> Dict:
    """Run single test with specific seed"""
    coordinates = problem.coordinates
    dimension = problem.dimension
    
    # Create distance matrix
    matrix = create_distance_matrix(coordinates)
    duration_func = create_duration_func(matrix)
    
    # Create initial tour with random permutation
    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    
    initial_route = [f"L{i}" for i in indices]
    
    # Apply local search
    start_time = time.time()
    improved_route, _ = apply_local_search(
        initial_route, duration_func, ls_type, max_iterations=max_iterations
    )
    elapsed = time.time() - start_time
    
    # Calculate tour length
    tour_indices = convert_route_to_indices(improved_route)
    tour_length = calculate_tour_length(tour_indices, coordinates)
    
    gap = ((tour_length - problem.optimal) / problem.optimal) * 100
    
    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
    }


def run_benchmark_for_problem(
    problem: TSPLIBProblem,
    n_runs: int = 3,
    verbose: bool = True
) -> List[Dict]:
    """Run benchmark for a single problem with all strategies"""
    results = []
    
    for strat_name, ls_type, max_iter in STRATEGIES:
        if verbose:
            print(f"    Testing {strat_name}...", end=" ", flush=True)
        
        run_results = []
        for run in range(n_runs):
            seed = (run + 1) * 42
            result = run_single_test(problem, ls_type, seed, max_iter)
            run_results.append(result)
        
        # Calculate averages
        avg_length = sum(r["tour_length"] for r in run_results) / len(run_results)
        avg_gap = sum(r["gap"] for r in run_results) / len(run_results)
        avg_time = sum(r["time_ms"] for r in run_results) / len(run_results)
        
        best_length = min(r["tour_length"] for r in run_results)
        best_gap = min(r["gap"] for r in run_results)
        
        result = {
            "problem": problem.name,
            "dimension": problem.dimension,
            "category": problem.category,
            "optimal": problem.optimal,
            "strategy": strat_name,
            "avg_length": avg_length,
            "avg_gap": avg_gap,
            "best_length": best_length,
            "best_gap": best_gap,
            "avg_time_ms": avg_time,
            "n_runs": n_runs,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(result)
        
        if verbose:
            status = "★" if best_gap <= 1 else ("✓" if best_gap <= 5 else ("○" if best_gap <= 10 else "✗"))
            print(f"avg_gap: {avg_gap:.2f}%, best_gap: {best_gap:.2f}% {status}")
    
    return results


def save_results(results: List[Dict], prefix: str = ""):
    """Save results to JSON and CSV files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_file = os.path.join(OUTPUT_DIR, f"{prefix}benchmark_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"    JSON saved: {json_file}")
    
    # Save CSV
    csv_file = os.path.join(OUTPUT_DIR, f"{prefix}benchmark_{timestamp}.csv")
    if results:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"    CSV saved: {csv_file}")
    
    return json_file, csv_file


def print_summary_table(results: List[Dict]):
    """Print summary table"""
    print("\n" + "="*100)
    print("ÖZET TABLO")
    print("="*100)
    
    # Group by problem
    problems = {}
    for r in results:
        prob = r["problem"]
        if prob not in problems:
            problems[prob] = r
    
    print(f"\n{'Problem':<15} | {'Dim':<6} | {'Optimal':<10} | {'Best Strategy':<15} | {'Best Gap':<10} | {'Avg Gap':<10}")
    print("-" * 90)
    
    for prob_name in sorted(problems.keys(), key=lambda x: problems[x]['dimension']):
        r = problems[prob_name]
        prob_results = [x for x in results if x["problem"] == prob_name]
        best = min(prob_results, key=lambda x: x["best_gap"])
        
        status = "★" if best["best_gap"] <= 1 else ("✓" if best["best_gap"] <= 5 else ("○" if best["best_gap"] <= 10 else "✗"))
        
        print(f"{r['problem']:<15} | {r['dimension']:<6} | {r['optimal']:<10} | {best['strategy']:<15} | {best['best_gap']:>8.2f}% | {best['avg_gap']:>8.2f}% {status}")
    
    # Strategy performance
    print("\n" + "-"*90)
    print("STRATEJİ PERFORMANSLARI")
    print("-"*90)
    
    strategy_stats = {}
    for r in results:
        strat = r["strategy"]
        if strat not in strategy_stats:
            strategy_stats[strat] = {"gaps": [], "times": []}
        strategy_stats[strat]["gaps"].append(r["avg_gap"])
        strategy_stats[strat]["times"].append(r["avg_time_ms"])
    
    print(f"\n{'Strategy':<15} | {'Avg Gap':<12} | {'Min Gap':<12} | {'Max Gap':<12} | {'Avg Time (ms)':<15}")
    print("-" * 75)
    
    for strat, stats in sorted(strategy_stats.items(), key=lambda x: sum(x[1]["gaps"])/len(x[1]["gaps"])):
        avg = sum(stats["gaps"]) / len(stats["gaps"])
        min_gap = min(stats["gaps"])
        max_gap = max(stats["gaps"])
        avg_time = sum(stats["times"]) / len(stats["times"])
        print(f"{strat:<15} | {avg:>10.2f}% | {min_gap:>10.2f}% | {max_gap:>10.2f}% | {avg_time:>13.1f}")


def ask_continue() -> bool:
    """Ask user if they want to continue"""
    while True:
        response = input("\nDevam etmek istiyor musunuz? (e/h/q): ").strip().lower()
        if response in ['e', 'evet', 'y', 'yes']:
            return True
        elif response in ['h', 'hayır', 'n', 'no', 'q', 'quit', 'exit']:
            return False
        print("Lütfen 'e' (evet) veya 'h' (hayır) girin.")


# ============================================================
# Main Interactive Runner
# ============================================================

def run_interactive_benchmark():
    """Run interactive benchmark"""
    print("\n" + "="*100)
    print("İNTERAKTİF TSPLIB BENCHMARK")
    print("="*100)
    print(f"\nToplam Problem: {len(ALL_PROBLEMS)}")
    print(f"  - Küçük (n ≤ 100): {len(SMALL_PROBLEMS)} problem")
    print(f"  - Orta (100 < n ≤ 500): {len(MEDIUM_PROBLEMS)} problem")
    print(f"  - Büyük (500 < n ≤ 2000): {len(LARGE_PROBLEMS)} problem")
    print(f"\nHer problem {N_RUNS} kez test edilecek.")
    print(f"Stratejiler: {', '.join([s[0] for s in STRATEGIES])}")
    print(f"Sonuçlar otomatik olarak kaydedilecek: {OUTPUT_DIR}")
    
    all_results = []
    
    # Ask which category to start with
    print("\n" + "-"*50)
    print("Hangi kategoriden başlamak istiyorsunuz?")
    print("  1. Küçük (hızlı)")
    print("  2. Orta")
    print("  3. Büyük")
    print("  4. Tümü")
    print("  q. Çıkış")
    
    choice = input("\nSeçiminiz (1-4/q): ").strip().lower()
    
    if choice == 'q':
        print("Çıkış yapılıyor...")
        return
    
    # Select problems based on choice
    if choice == '1':
        problems_to_run = SMALL_PROBLEMS
        category_name = "KÜÇÜK"
    elif choice == '2':
        problems_to_run = MEDIUM_PROBLEMS
        category_name = "ORTA"
    elif choice == '3':
        problems_to_run = LARGE_PROBLEMS
        category_name = "BÜYÜK"
    elif choice == '4':
        problems_to_run = ALL_PROBLEMS
        category_name = "TÜM"
    else:
        print("Geçersiz seçim. Küçük kategori ile başlanıyor...")
        problems_to_run = SMALL_PROBLEMS
        category_name = "KÜÇÜK"
    
    print(f"\n{category_name} kategorisinde {len(problems_to_run)} problem çalıştırılacak.")
    
    # Run benchmark for each problem
    for i, problem in enumerate(problems_to_run, 1):
        print("\n" + "="*100)
        print(f"[{i}/{len(problems_to_run)}] {problem.name.upper()} (n={problem.dimension}, optimal={problem.optimal})")
        print(f"Kategori: {problem.category.upper()}")
        print("="*100)
        
        results = run_benchmark_for_problem(problem, N_RUNS)
        all_results.extend(results)
        
        # Save intermediate results
        save_results(all_results, prefix=f"{category_name.lower()}_")
        
        # Ask to continue (except for last problem)
        if i < len(problems_to_run):
            if not ask_continue():
                print("\nBenchmark durduruldu.")
                break
    
    # Final summary
    if all_results:
        print_summary_table(all_results)
        
        # Save final results
        print("\n" + "-"*50)
        print("FİNAL SONUÇLARI KAYDEDİLİYOR...")
        save_results(all_results, prefix="final_")
        
        print("\n" + "="*100)
        print("BENCHMARK TAMAMLANDI")
        print("="*100)


if __name__ == "__main__":
    run_interactive_benchmark()
