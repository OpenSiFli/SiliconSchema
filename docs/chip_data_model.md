# 芯片结构化数据分类与规范

## 概念分层与合理性

1. **Series（系列）**：描述一簇逻辑上共享同一架构/寄存器映射的芯片。`series.yaml` 体现系列级别的公共元数据（版本、生命周期、资料链接等），避免在每个具体料号上重复描述。
2. **Pad（晶圆焊盘）**：晶圆上的原子实体，是唯一能被 Bond 到封装引脚的对象。一个 pad 具有确定的电气类型（来自 `common/enums.yml` 中的 `pin_types`），并且维护自身的复用能力（pinmux）。pad 级别的抽象让我们可以在多个封装/料号之间重用相同的物理资源定义。
3. **Pinmux（复用路径）**：属于 pad 的数组，元素包含 `{function, select}`。`function` 采用 `外设_信号` 的命名方式（必要时可省略 `_信号` 以表示外设下所有信号均可路由），`select` 标识路由编号，对应 GPIO 控制器的复用寄存器实际写值。允许不同的 `function` 使用相同的 `select`，表示选择该编号后后续由子复用矩阵完成信号分发。
4. **Variant（变体/料号）**：指定唯一的 `part_number` 与封装信息，体现同一系列下不同容量、存储器配置或封装的产品。变体引用系列级别的 pad 定义，通过 `pins` 阵列把封装引脚编号映射到 pad。
5. **Pin（封装引脚）**：属于某个变体，描述封装丝印/编号 `number` 与所连接的 `pad`。引脚可以连接到同一个 pad（多引脚并联）或多个 pad（特殊封装需求，例如冗余供电），因此 `pin.pad` 支持 YAML Anchor/别名直接复用 `pads` 中的定义。

该分层确保：
- pad/pin 的职责分离：pad 负责晶圆级电气能力，pin 负责封装级拓扑，实现跨封装/跨料号的最大复用；
- pinmux 聚合在 pad 下，避免在每个变体里重复罗列复用信息；
- 变体独立声明封装定义，便于后续 BOM、封装库以及 PCB 脚位图生成。

## 文件与字段约定

`chips/<series>/series.yaml` 采用 YAML 结构，建议字段顺序如下：

```yaml
schema_version: 0.0.1          # 与 JSON Schema 同步的版本号
model_id: SF32LB52x            # 系列唯一标识
lifecycle: production|...      # 生命周期枚举，可拓展
docs:                          # 资料链接列表，可按语言细化
  - datasheet: { zh: "...", en: "..." }

pads:                          # map，键为 pad 名称
  PA00:
    type: bidirectional        # 来自 common/enums.yml 的 pin_types
    pinmux:
      - { function: GPIO, select: 0 }
      - { function: UART_RX, select: 4 }
  ...

variants:                      # 料号列表
  - part_number: SF32LB520U36
    description: "8Mb NOR Flash"
    package: QFN-68-1EP_7x7mm_P0.35mm_EP5.49x5.49mm
    pins:
      - number: 1
        pad: *PA00             # 通过 YAML Anchor 引用 pad
```

### 约束补充

- `schema_version` 与 JSON Schema 中的 `$defs.version` 同步维护。
- `docs` 数组元素可根据需要扩展为 `datasheet`、`user_manual` 等不同类型，每个字段允许按语言拆分。
- `pinmux.function` 推荐使用大写下划线命名；`select` 为非负整数。
- `pins.number` 允许字符串（如 BGA `A3`）或整数，但在 JSON Schema 中统一表示为字符串（即使是数字也写成字符串），以兼容含字母脚位。
- 如需在 pin/pad 上附加特殊说明，可扩展 `notes`（字符串）字段，JSON Schema 已预留 `description`/`notes` 之类的可选属性。

## JSON Schema

`common/schema/chip-series.schema.json` 给出了对 `series.yaml` 的机器可校验规范（基于 JSON Schema draft 2020-12）。推荐在 CI 中通过 `yajsv`, `ajv` 等工具将 YAML 转 JSON 后执行校验，保证所有新芯片遵循上述约定。
