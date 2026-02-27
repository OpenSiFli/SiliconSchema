# SiliconSchema

SiFli 芯片结构化数据仓库，包含芯片引脚定义、复用配置和变体信息。

## 快速开始

```bash
# 安装依赖
uv sync

# 构建所有芯片
uv run build-schema

# 验证生成的文件
uv run validate-schema
```

## 目录结构

```
SiliconSchema/
├── common/
│   ├── schema/                    # JSON Schema 定义
│   │   └── chip-series.schema.json
│   └── pinmux/                    # 共享 pinmux 配置
│       └── sf32lb52/
│           ├── pinmux.yaml        # GPIO 复用功能
│           └── pinr.yaml          # PINR 寄存器定义
├── chips/                         # 芯片专属配置（源文件）
│   ├── SF32LB52x/
│   │   └── chip.yaml
│   └── SF32LB52_X/
│       └── chip.yaml
├── out/                           # 构建输出（.gitignore）
│   └── <chip>/
│       ├── series.yaml            # 完整芯片定义
│       └── <model_id>-pinctrl.h   # Zephyr pinctrl 头文件（部分系列可选）
└── docs/
    └── chip_data_model.md         # 数据模型文档
```

## 命令行工具

### build-schema

构建 `series.yaml` 和 Zephyr pinctrl 头文件。

```bash
# 构建所有芯片
uv run build-schema

# 构建单个芯片
uv run build-schema -c SF32LB52x
uv run build-schema --chip SF32LB52x
```

**参数：**
| 参数 | 说明 |
|------|------|
| `-c`, `--chip` | 指定芯片目录名（默认构建所有芯片） |

**输出：**
- `out/<chip>/series.yaml` — 合并后的完整芯片定义
- `out/<chip>/<model_id>-pinctrl.h` — Zephyr pinctrl 头文件（可选；`sf32lb56`/`sf32lb58` 不生成）

### validate-schema

验证生成的 `series.yaml` 是否符合 JSON Schema。

```bash
# 验证所有芯片
uv run validate-schema

# 验证单个芯片
uv run validate-schema -c SF32LB52x
uv run validate-schema --chip SF32LB52x

# 详细输出
uv run validate-schema -v
uv run validate-schema --verbose
```

**参数：**
| 参数 | 说明 |
|------|------|
| `-c`, `--chip` | 指定芯片目录名（默认验证所有芯片） |
| `-v`, `--verbose` | 显示详细验证信息 |

## 数据模型

详见 [docs/chip_data_model.md](docs/chip_data_model.md)

### 核心概念

- **Pad（焊盘）**：晶圆级引脚，包含电气类型和功能列表
- **Functions（功能）**：Pad 支持的复用功能（GPIO、I2C、UART、TIM 等）
- **PINR（二次路由）**：I2C/UART/TIM 需要的额外寄存器配置
- **Variant（变体）**：不同封装/容量的具体料号
- **Pin（引脚）**：封装级引脚，映射到 Pad

### 示例：series.yaml

```yaml
pads:
  PA00: &PA00
    type: bidirectional
    functions:
      - GPIO_A0
      - I2C1_SDA
      - I2C1_SCL
      - USART1_TXD
      - GPTIM1_CH1

variants:
  - part_number: SF32LB520U36
    package: QFN-68
    pins:
      - {number: "1", pad: *PA32}
```

### 示例：pinctrl 头文件

```c
#define PA00_ANALOG             SF32LB_PINMUX_ANALOG(PA, 0U)
#define PA00_GPIO               SF32LB_PINMUX(PA, 0U, 0U, 0U, 0U)
#define PA00_I2C1_SDA           SF32LB_PINMUX(PA, 0U, 4U, 0x48U, 1U)
#define PA00_USART1_TXD         SF32LB_PINMUX(PA, 0U, 4U, 0x58U, 0U)
```

## 添加新芯片

1. 在 `chips/` 下创建新目录
2. 创建 `chip.yaml`，引用共享 pinmux
3. 运行 `uv run build-schema -c <chip_name>`
4. 运行 `uv run validate-schema -c <chip_name>`

## License

Apache-2.0
