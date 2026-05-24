# Intel Server & Workstation CPU Reference

## Intel Xeon Scalable Processors (Server)

### 6th Gen Intel Xeon (Granite Rapids) — 2024
- **Socket**: LGA 4710 / LGA 4677
- **Codename**: Granite Rapids-P (P-core), Granite Rapids-AP (e-core)
- **Series**: Xeon 6700-P, Xeon 6500-P (P-core); Xeon 6700-E, Xeon 6500-E (E-core)
- **Process**: Intel 3
- **Max Cores**: 128P-cores or 288E-cores per socket
- **Max Memory**: 8-channel DDR5-6400, up to 8TB per socket
- **PCIe**: PCIe 5.0 x96 per socket
- **TDP Range**: 205W – 500W
- **Key Features**: Intel Advanced Matrix Extensions (AMX), Intel Data Streaming Accelerator (DSA), Intel In-Memory Analytics Accelerator (IAA), HBM option
- **Max Sockets**: 2S (P-core), 1S (E-core high density)
- **Use Cases**: AI inference, cloud, database, HPC, general purpose data center

### 5th Gen Intel Xeon Scalable (Emerald Rapids) — 2024
- **Socket**: LGA 4677 (SP5 compatible replacement for SPR)
- **Codename**: Emerald Rapids
- **Series**: Xeon Platinum 8500, Gold 6500/5500, Silver 4500, Bronze 3500
- **Process**: Intel 7 (10nm ESF)
- **Max Cores**: 64 cores per socket
- **Max Memory**: 8-channel DDR5-4800, up to 4TB per socket
- **PCIe**: PCIe 5.0 x80 per socket
- **TDP Range**: 60W – 350W
- **Key Features**: AMX (BF16/INT8), Intel DLB, Intel QAT, HBM option (Xeon CPU Max 9500)
- **Max Sockets**: 8S
- **Popular Models**: Xeon Platinum 8592+, 8562Y+, Gold 6554S, 6548N

### 4th Gen Intel Xeon Scalable (Sapphire Rapids) — 2023
- **Socket**: LGA 4677
- **Codename**: Sapphire Rapids
- **Series**: Xeon Platinum 8400/9400, Gold 6400/5400, Silver 4400, Bronze 3400
- **Process**: Intel 7 (10nm ESF)
- **Max Cores**: 60 cores per socket
- **Max Memory**: 8-channel DDR5-4800, up to 4TB per socket
- **PCIe**: PCIe 5.0 x80 per socket
- **TDP Range**: 60W – 350W
- **Key Features**: AMX (first gen), HBM (Xeon CPU Max 9400 series), CXL 1.1
- **Max Sockets**: 8S
- **Popular Models**: Xeon Platinum 8480+, 8468, Gold 6448Y, 5420+, Silver 4416+

### 3rd Gen Intel Xeon Scalable (Ice Lake-SP) — 2021
- **Socket**: LGA 4189 (P+)
- **Codename**: Ice Lake-SP
- **Series**: Xeon Platinum 8300/9300, Gold 6300/5300, Silver 4300, Bronze 3300
- **Process**: Intel 10nm SuperFin
- **Max Cores**: 40 cores per socket
- **Max Memory**: 8-channel DDR4-3200, up to 6TB per socket
- **PCIe**: PCIe 4.0 x64 per socket
- **TDP Range**: 125W – 270W
- **Key Features**: DL Boost (VNNI), Intel SHPC, SGX
- **Max Sockets**: 8S
- **Popular Models**: Xeon Platinum 8380, 8368Q, Gold 6338, 6330, Silver 4316

### 2nd Gen Intel Xeon Scalable (Cascade Lake) — 2019
- **Socket**: LGA 3647
- **Codename**: Cascade Lake-SP / -AP
- **Series**: Xeon Platinum 8200/9200, Gold 6200/5200, Silver 4200, Bronze 3200
- **Process**: Intel 14nm++
- **Max Cores**: 28 cores per socket (SP), 56 cores (AP with 2 dies)
- **Max Memory**: 6-channel DDR4-2933, up to 4.5TB per socket
- **PCIe**: PCIe 3.0 x48 per socket
- **TDP Range**: 85W – 400W
- **Key Features**: DL Boost (VNNI first gen), Intel Optane DC Persistent Memory support
- **Max Sockets**: 8S
- **Popular Models**: Xeon Platinum 8280, Gold 6254, 6226R, Silver 4214R

---

## Intel Xeon W (Workstation/HEDT)

### Intel Xeon W-3400 Series (Sapphire Rapids-W) — 2023
- **Socket**: LGA 4677
- **Codename**: Sapphire Rapids-W
- **Models**: W9-3595X (60C), W9-3575X (52C), W7-3465X (28C), W5-3435X (16C), W3-3423 (12C)
- **Process**: Intel 7
- **Max Memory**: 8-channel DDR5-4800, up to 2TB ECC
- **PCIe**: PCIe 5.0 x112
- **TDP**: 270W–350W (W9), 200W (W7), 150W (W5/W3)
- **Key Features**: AMX, ECC memory, PCIe 5.0, CXL, Thunderbolt 4
- **Platform**: Intel W790 chipset
- **Use Cases**: CAD/CAM, AI workstation, rendering, simulation

### Intel Xeon W-2400 Series (Sapphire Rapids-W) — 2023
- **Socket**: LGA 4677
- **Models**: W9-2595X (24C), W7-2495X (24C), W7-2475X (20C), W5-2465X (16C), W3-2425 (6C)
- **Process**: Intel 7
- **Max Memory**: 8-channel DDR5-4800, up to 1TB ECC
- **PCIe**: PCIe 5.0 x64
- **TDP**: 270W (W9), 200W (W7), 150W (W5/W3)
- **Platform**: Intel W680 chipset (mainstream workstation)
- **Use Cases**: Entry workstation, simulation, content creation

### Intel Xeon W-1300 Series (Alder Lake-S) — 2022
- **Socket**: LGA 1700
- **Models**: W-1390 (8C), W-1350P (6C), W-1370 (8C), W-1350 (6C)
- **Process**: Intel 7 (10nm)
- **Max Memory**: DDR4-3200 or DDR5-4800, 2 channels, up to 128GB ECC
- **PCIe**: PCIe 5.0 x16 (CPU), PCIe 4.0 (PCH)
- **TDP**: 80W–125W
- **Platform**: Intel W680 chipset
- **Use Cases**: Entry-level workstation, embedded industrial

---

## Quick Reference: Socket Compatibility

| Generation       | Socket     | DDR Gen | PCIe Gen |
|-----------------|------------|---------|----------|
| Xeon 6 (GNR)   | LGA 4710   | DDR5    | PCIe 5.0 |
| 5th Gen (EMR)  | LGA 4677   | DDR5    | PCIe 5.0 |
| 4th Gen (SPR)  | LGA 4677   | DDR5    | PCIe 5.0 |
| 3rd Gen (ICX)  | LGA 4189   | DDR4    | PCIe 4.0 |
| 2nd Gen (CLX)  | LGA 3647   | DDR4    | PCIe 3.0 |
| Xeon W-3400    | LGA 4677   | DDR5    | PCIe 5.0 |
| Xeon W-2400    | LGA 4677   | DDR5    | PCIe 5.0 |
| Xeon W-1300    | LGA 1700   | DDR4/5  | PCIe 5.0 |

## TOR Matching Keywords

- "Xeon 6" / "Granite Rapids" / "6700" / "6500" → 6th Gen Xeon
- "Emerald Rapids" / "8500" / "6500 series" → 5th Gen Xeon
- "Sapphire Rapids" / "8400" / "8480" / "4th Gen Xeon" → 4th Gen Xeon
- "Ice Lake" / "3rd Gen Xeon" / "8380" / "6338" → 3rd Gen Xeon
- "Cascade Lake" / "2nd Gen Xeon" / "8280" / "6226" → 2nd Gen Xeon
- "Xeon W-3400" / "W9-3595X" → W-3400 series
- "Xeon W-2400" / "W9-2495X" → W-2400 series
- "Xeon W-1300" / "W-1390" → W-1300 series
