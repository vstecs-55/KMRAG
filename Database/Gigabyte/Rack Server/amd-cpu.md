# AMD Server & Workstation CPU Reference

## AMD EPYC Processors (Server)

### AMD EPYC 9005 Series "Turin" — 2024 (Current Gen)
- **Socket**: SP5 (LGA 6096)
- **Codename**: Turin (Zen 5 / Zen 5c hybrid)
- **Series**: EPYC 9965, 9955, 9935, 9915, 9755, 9745, 9565, 9555, 9554, 9534, 9474F, 9454P, 9374F...
- **Process**: TSMC 3nm (Zen 5) / 4nm (Zen 5c)
- **Max Cores**: 192 cores per socket (Turin) / 128 cores (Turin-X with 3D V-Cache)
- **Max Memory**: 12-channel DDR5-6400, up to 6TB per socket
- **PCIe**: PCIe 5.0 x160 per socket
- **TDP Range**: 200W – 500W
- **Max Sockets**: 2S
- **Key Features**: Zen 5 IPC improvements, 3D V-Cache option, AVX-512
- **Use Cases**: AI/ML, HPC, cloud, virtualization, database, SAP HANA

### AMD EPYC 9004 Series "Genoa" — 2022
- **Socket**: SP5 (LGA 6096)
- **Codename**: Genoa (Zen 4)
- **Series**: EPYC 9654, 9554, 9474F, 9454, 9374F, 9354, 9334, 9254, 9224, 9174F, 9124, 9754S
- **Process**: TSMC 5nm
- **Max Cores**: 96 cores per socket
- **Max Memory**: 12-channel DDR5-4800, up to 6TB per socket
- **PCIe**: PCIe 5.0 x128 per socket
- **TDP Range**: 155W – 400W
- **Max Sockets**: 2S (SP5), 1S (SP5s for 9754S)
- **Key Features**: AVX-512, CXL 1.1, Zen 4 architecture
- **Popular Models**: EPYC 9654 (96C), 9554 (64C), 9454 (48C), 9354P (32C/1P)

### AMD EPYC 9004X Series "Genoa-X" — 2023
- **Socket**: SP5 (LGA 6096)
- **Codename**: Genoa-X (Zen 4 + 3D V-Cache)
- **Series**: EPYC 9684X (96C, 1152MB cache), 9384X (32C), 9184X (16C)
- **Process**: TSMC 5nm + 3D V-Cache
- **Max Cores**: 96 cores per socket
- **Max Memory**: 12-channel DDR5-4800, up to 6TB per socket
- **PCIe**: PCIe 5.0 x128 per socket
- **TDP Range**: 250W – 400W
- **Key Features**: 3D V-Cache for cache-sensitive HPC/EDA/rendering workloads
- **Use Cases**: EDA, financial simulations, gaming server, technical computing

### AMD EPYC 7003 Series "Milan" — 2021
- **Socket**: SP3 (LGA 4094)
- **Codename**: Milan (Zen 3) / Milan-X (Zen 3 + 3D V-Cache)
- **Series**: EPYC 7763, 7713, 7663, 7643, 7543, 7513, 7453, 7343, 7313, 7203
- **Process**: TSMC 7nm
- **Max Cores**: 64 cores per socket
- **Max Memory**: 8-channel DDR4-3200, up to 4TB per socket
- **PCIe**: PCIe 4.0 x128 per socket
- **TDP Range**: 120W – 280W
- **Max Sockets**: 2S (P), 1S (F single-socket)
- **Popular Models**: EPYC 7763 (64C/128T), 7713 (64C), 7543 (32C), 7313P (16C, 1P)
- **Milan-X Models**: EPYC 7773X, 7573X, 7473X (3D V-Cache)

### AMD EPYC 7002 Series "Rome" — 2019
- **Socket**: SP3 (LGA 4094)
- **Codename**: Rome (Zen 2)
- **Series**: EPYC 7742, 7702, 7662, 7642, 7552, 7542, 7502, 7452, 7402, 7352, 7302, 7252
- **Process**: TSMC 7nm
- **Max Cores**: 64 cores per socket
- **Max Memory**: 8-channel DDR4-3200, up to 4TB per socket
- **PCIe**: PCIe 4.0 x128 per socket
- **TDP Range**: 120W – 280W
- **Max Sockets**: 2S
- **Popular Models**: EPYC 7742 (64C), 7702 (64C), 7502 (32C), 7302 (16C)

### AMD EPYC 8004 Series "Siena" — 2023 (Edge/1P)
- **Socket**: SP6 (LGA 4844)
- **Codename**: Siena (Zen 4c — compact cores)
- **Series**: EPYC 8534P (64C), 8474P (48C), 8434P (48C), 8374P (32C), 8324P (32C), 8274P (24C), 8224P (24C), 8124P (16C)
- **Process**: TSMC 4nm (Zen 4c)
- **Max Cores**: 64 cores per socket (1S only)
- **Max Memory**: 6-channel DDR5-4800, up to 1.5TB
- **PCIe**: PCIe 5.0 x96 per socket
- **TDP Range**: 135W – 200W
- **Max Sockets**: 1S only
- **Key Features**: Lower TDP, smaller socket, ideal for edge and telco deployments
- **Use Cases**: Edge computing, CDN, telco NFV, dense 1U servers

---

## AMD Ryzen Threadripper PRO (Workstation HEDT)

### Ryzen Threadripper PRO 7000 Series "Storm Peak" — 2023
- **Socket**: sWRX90 (LGA 6096)
- **Models**: Threadripper PRO 7995WX (96C), 7985WX (64C), 7975WX (32C), 7965WX (24C), 7955WX (16C), 7945WX (12C)
- **Process**: TSMC 5nm (Zen 4)
- **Max Memory**: 8-channel DDR5-5200, up to 2TB ECC RDIMM
- **PCIe**: PCIe 5.0 x48 (CPU lanes)
- **TDP**: 350W (7995WX), 350W (7985WX), 350W (7975WX), 280W (lower models)
- **Key Features**: ECC support, massive core count, large L3 cache, AVX-512
- **Platform**: WRX90 chipset (ASUS Pro WS / Supermicro M12SWA-TF compatible)
- **Use Cases**: 3D rendering, AI training, video production, CAD, simulation

### Ryzen Threadripper PRO 5000 Series "Chagall" — 2022
- **Socket**: sWRX80 (LGA 4094)
- **Models**: Threadripper PRO 5995WX (64C), 5975WX (32C), 5965WX (24C), 5955WX (16C), 5945WX (12C)
- **Process**: TSMC 7nm (Zen 3)
- **Max Memory**: 8-channel DDR4-3200, up to 2TB ECC RDIMM
- **PCIe**: PCIe 4.0 x128
- **TDP**: 280W
- **Key Features**: ECC support, WX80 platform, RDIMM compatibility
- **Platform**: WRX80 chipset (ASUS Pro WS WRX80E, Supermicro M12SWA-TF)
- **Use Cases**: 3D rendering, workstation AI, engineering simulation

---

## Quick Reference: Socket Compatibility

| Series                  | Socket  | DDR Gen | PCIe Gen | Max Sockets |
|------------------------|---------|---------|----------|-------------|
| EPYC 9005 (Turin)      | SP5     | DDR5    | PCIe 5.0 | 2S          |
| EPYC 9004 (Genoa)      | SP5     | DDR5    | PCIe 5.0 | 2S          |
| EPYC 9004X (Genoa-X)   | SP5     | DDR5    | PCIe 5.0 | 2S          |
| EPYC 7003 (Milan)      | SP3     | DDR4    | PCIe 4.0 | 2S          |
| EPYC 7002 (Rome)       | SP3     | DDR4    | PCIe 4.0 | 2S          |
| EPYC 8004 (Siena)      | SP6     | DDR5    | PCIe 5.0 | 1S          |
| TR PRO 7000            | sWRX90  | DDR5    | PCIe 5.0 | 1S WS       |
| TR PRO 5000            | sWRX80  | DDR4    | PCIe 4.0 | 1S WS       |

## TOR Matching Keywords

- "EPYC 9005" / "Turin" / "Zen 5" / "9654" / "9554" / "9974F" → EPYC 9005 series
- "EPYC 9004" / "Genoa" / "Zen 4" / "9654" / "9354P" → EPYC 9004 series
- "EPYC 9684X" / "Genoa-X" / "3D V-Cache" → EPYC 9004X series
- "EPYC 7003" / "Milan" / "Zen 3" / "7763" / "7513" → EPYC 7003 series
- "EPYC 7002" / "Rome" / "Zen 2" / "7742" / "7502" → EPYC 7002 series
- "EPYC 8004" / "Siena" / "SP6" / "Zen 4c" → EPYC 8004 series
- "Threadripper PRO 7000" / "7995WX" / "Storm Peak" → TR PRO 7000
- "Threadripper PRO 5000" / "5995WX" / "Chagall" → TR PRO 5000
