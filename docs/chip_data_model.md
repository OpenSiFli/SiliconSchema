# 芯片结构化数据分类与规范

## 概念分层与合理性

1. **Series（系列）**：描述一簇逻辑上共享同一架构/寄存器映射的芯片。`series.yaml` 体现系列级别的公共元数据（版本、生命周期、资料链接等），避免在每个具体料号上重复描述。
2. **Pad（晶圆焊盘）**：晶圆上的原子实体，是唯一能被 Bond 到封装引脚的对象。一个 pad 具有确定的电气类型（由 JSON Schema 中的 `pinType` 枚举约束），并且维护自身的复用能力（functions）。pad 级别的抽象让我们可以在多个封装/料号之间重用相同的物理资源定义。
3. **Functions（功能列表）**：属于 pad 的数组，列出该 pad 支持的所有功能。包括直接功能（如 `GPIO_A0`、`LCDC1_SPI_RSTB`）和需要 PINR 二次路由的功能（如 `I2C1_SDA`、`USART1_TXD`、`GPTIM1_CH1`）。
4. **PINR（二次路由寄存器）**：用于 I2C、UART、TIM 等外设的信号路由。这些外设需要两级配置：首先将 pad 的 function select 设置为对应类型（如 I2C=4），然后通过 PINR 寄存器指定具体外设信号连接到哪个 pad。
5. **Variant（变体/料号）**：指定唯一的 `part_number` 与封装信息，体现同一系列下不同容量、存储器配置或封装的产品。变体引用系列级别的 pad 定义，通过 `pins` 阵列把封装引脚编号映射到 pad。
6. **Pin（封装引脚）**：属于某个变体，描述封装丝印/编号 `number` 与所连接的 `pad`。引脚可以连接到同一个 pad（多引脚并联）或多个 pad（特殊封装需求），因此 `pin.pad` 支持 YAML Anchor/别名直接复用 `pads` 中的定义。

该分层确保：
- pad/pin 的职责分离：pad 负责晶圆级电气能力，pin 负责封装级拓扑，实现跨封装/跨料号的最大复用；
- functions 聚合在 pad 下，避免在每个变体里重复罗列复用信息；
- 变体独立声明封装定义，便于后续 BOM、封装库以及 PCB 脚位图生成。

---

## 目录结构

```
SiliconSchema/
├── common/
│   ├── schema/
│   │   └── chip-series.schema.json    # 输出文件的 JSON Schema
│   └── pinmux/
│       └── sf32lb52/
│           ├── pinmux.yaml            # 共享 pinmux 定义（源文件）
│           └── pinr.yaml              # PINR 寄存器定义
├── chips/
│   ├── SF32LB52x/
│   │   └── chip.yaml                  # 芯片专属定义（源文件）
│   └── SF32LB52_X/
│       └── chip.yaml
├── out/                               # 构建输出目录（.gitignore）
│   ├── SF32LB52x/
│   │   └── series.yaml                # 生成的完整定义
│   └── SF32LB52_X/
│       └── series.yaml
├── src/silicon_schema/                # Python 构建工具
│   ├── build.py
│   └── validate.py
└── pyproject.toml                     # uv 项目配置
```

---

## 源文件格式

### chip.yaml（芯片专属定义）

```yaml
schema_version: 0.0.1
model_id: SF32LB52x
lifecycle: production
shared_pinmux: sf32lb52           # 引用共享 pinmux

docs:
  - datasheet:
      zh: "https://..."
      en: "https://..."

# GPIO Pads（仅定义 type，pinmux 从共享文件合并）
pads:
  PA00: {type: bidirectional}
  PA01: {type: bidirectional}
  # ...

  # 电源/模拟专用 Pads（完整定义）
  VBUS:
    type: power_input
    description: "VBUS input"
  # ...

variants:
  - part_number: SF32LB520U36
    description: "8Mb NOR Flash"
    package: QFN-68-1EP_7x7mm_P0.35mm_EP5.49x5.49mm
    pins:
      - {number: "1", pad: PA32}
      - {number: "2", pad: PA31}
      # ...
```

### pinmux.yaml（共享 pinmux 定义）

```yaml
# pinr: true 表示该功能需要通过 PINR 寄存器进行二次路由
pinmux:
  PA00:
    - {function: GPIO_A0, select: 0}
    - {function: LCDC1_SPI_RSTB, select: 1}
    - {function: I2C, select: 4, pinr: true}
    - {function: UART, select: 4, pinr: true}
    - {function: TIM, select: 5, pinr: true}
    - {function: LCDC1_8080_RSTB, select: 7}
```

### pinr.yaml（PINR 寄存器定义）

```yaml
registers:
  I2C1_PINR:
    offset: 0x48
    fields:
      SDA: {bits: [13, 8]}
      SCL: {bits: [5, 0]}

  USART1_PINR:
    offset: 0x58
    fields:
      CTS: {bits: [29, 24]}
      RTS: {bits: [21, 16]}
      RXD: {bits: [13, 8]}
      TXD: {bits: [5, 0]}

  GPTIM1_PINR:
    offset: 0x64
    fields:
      CH4: {bits: [29, 24]}
      CH3: {bits: [21, 16]}
      CH2: {bits: [13, 8]}
      CH1: {bits: [5, 0]}
  # ...

peripherals:
  I2C:
    instances: [I2C1, I2C2, I2C3, I2C4]
    signals: [SDA, SCL]

  UART:
    instances: [USART1, USART2, USART3]
    signals: [TXD, RXD, CTS, RTS]

  TIM:
    instances: [GPTIM1, GPTIM2, LPTIM1, LPTIM2, ATIM1]
    signals_by_instance:
      GPTIM1: [CH1, CH2, CH3, CH4, ETR]
      ATIM1: [CH1, CH2, CH3, CH4, CH1N, CH2N, CH3N, ETR, BK, BK2]
```

---

## 输出文件格式

### series.yaml（生成的完整定义）

由构建脚本合并 `chip.yaml` 和共享 pinmux 后生成：

```yaml
schema_version: 0.0.1
model_id: SF32LB52x
lifecycle: production

docs:
  - datasheet: {zh: "...", en: "..."}

pads:
  PA00: &PA00
    type: bidirectional
    functions:
      - GPIO_A0
      - LCDC1_SPI_RSTB
      - I2C1_SDA
      - I2C1_SCL
      - I2C2_SDA
      - I2C2_SCL
      # ... 所有 I2C 实例
      - USART1_TXD
      - USART1_RXD
      # ... 所有 UART 实例
      - GPTIM1_CH1
      - GPTIM1_CH2
      # ... 所有 TIM 实例
      - LCDC1_8080_RSTB

  VBUS: &VBUS
    type: power_input
    description: "VBUS input"

variants:
  - part_number: SF32LB520U36
    description: "8Mb NOR Flash"
    package: QFN-68-1EP_7x7mm_P0.35mm_EP5.49x5.49mm
    pins: &SF32LB52x_QFN68_PINS
      - {number: "1", pad: *PA32}
      - {number: "2", pad: *PA31}
      # ...

  - part_number: SF32LB523UB6
    pins: *SF32LB52x_QFN68_PINS    # 复用相同引脚定义
```

---

## 约束补充

- `schema_version` 与 JSON Schema 中的版本同步维护。
- `docs` 数组元素可扩展为 `datasheet`、`user_manual` 等类型，每个字段允许按语言拆分。
- `functions` 使用大写下划线命名（如 `I2C1_SDA`、`GPTIM1_CH1`）。
- `pins.number` 统一为字符串类型（即使是数字也写成 `"1"`），以兼容 BGA 字母脚位。
- 如需在 pin/pad 上附加特殊说明，可扩展 `notes` 或 `description` 字段。

---

## 构建与验证

使用 uv 管理的 Python 工具链：

```bash
# 构建所有芯片的 series.yaml
uv run build-schema

# 构建单个芯片
uv run build-schema -c SF32LB52x

# 验证生成的 YAML 符合 JSON Schema
uv run validate-schema
```

---

## JSON Schema

`common/schema/chip-series.schema.json` 给出了对 `series.yaml` 的机器可校验规范（基于 JSON Schema draft 2020-12）。推荐在 CI 中运行 `uv run validate-schema` 保证所有新芯片遵循上述约定。
