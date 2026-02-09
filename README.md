# A股月度因子投资框架

一个面向 **A 股月频因子投资/选股** 的轻量级研究与回测框架：  
- **会编程 / 因子投资**：按“因子构建 → 因子处理/回归预测 → 权重求解 → 回测 → 实盘预测”的流程自定义扩展。  
- **不想写代码**：直接在 `result/` 目录查看我已跑出的策略 **选股结果** 与 **历史收益表现**，作为参考。

> ⚠️ **免责声明**  
> 本仓库所有结果均由程序生成，仅供学习与研究参考，不构成任何投资建议。投资有风险，入市需谨慎。

---

## ✨ 框架能做什么

- **数据层**：读取/组织月度行情与财务数据
- **因子层**：内置常见月度因子 + 支持用户自定义因子
- **因子实验室（factor_lab）**：
  - 回归/建模预测 **预期收益率**
  - 预测/估计 **风险**
  - 求解组合最优权重
- **策略与回测**：
  - 内置因子投资策略回测 
  - 支持自定义策略
- **结果保存**：回测运行保存到 `strategies/record/`；策略展示产物放在 `result/`

---

## 🚀 快速开始

本项目提供了完整示例：`hello.ipynb`。

### 安装依赖
```bash
pip install -r requirements.txt
```

### 按流程运行 -- 详情见 `hello.ipynb`

核心流程只有三步：

#### Step A：选择/构建因子

内置因子示例（节选）：

* `Market()`、`Size()`、`Value()`、`Turnover()`、`Momentum()`、`FScore()`、`MScore()`、`Industry()`

自定义因子也支持（将你计算好的 CSV 放到 `./factors/factor_data/`，并保证文件名与因子名一致）。

#### Step B：预测收益/风险 + 求解权重（factor_lab）

* 预测收益：`factor_lab.revenue(vals, period=12)`
* 预测风险：`factor_lab.risk(vals, period=36)`
* 权重求解：`factor_lab.mvw(pred, rsk, lam=20)`

生成的结果一般保存到 `factors/weight/`（例如 `prediction*.csv`、`w*.csv`），便于策略直接读取。

#### Step C：策略回测

* 直接用“预期收益率”回测：`StgPred`
* 直接用“权重文件”回测：`StgWeight`
* 或继承 `Strategy` 自定义自己的交易/换仓逻辑

---

## 🧭 推荐使用路径 -- 给两类用户

### A) 研究/开发者

你可以按下面的“标准流水线”使用本框架：

1. **构建因子**：`factors/factor_builder/`（或直接接入你已有 CSV 因子）
2. **因子处理与建模**：`factors/factor_lab/`
3. **产出策略输入**：`factors/weight/`（如 `prediction.csv` / `w.csv`）
4. **回测与记录**：`strategies/` + `strategies/record/`
5. **实盘预测**：`real_trading/`

### B) 非技术用户

直接打开：

* `result/`：策略说明、收益曲线、每期选股明细。

---

## 📁 目录结构 -- 按功能划分

```text
Quantification-in-A-share/
├── dataset/                # 数据文件（行情/财务/指数等）
├── data_api/               # 数据接口层（可对接数据库/本地数据）
├── factors/                # 因子体系
│   ├── factor_builder/     # 因子构建（生成原始因子变量）
│   ├── factor_data/        # 已构建好的因子CSV（可手动放入自定义因子）
│   ├── factor_lab/         # 因子实验室：回归/预测/风险/权重求解等
│   └── weight/             # 因子处理产物：prediction.csv、w.csv 等
├── strategies/             # 回测框架与策略实现
│   ├── record/             # 每次回测运行的详细记录（自动生成）
│   └── strategy.py         # Strategy基类（自定义策略建议从这里开始）
├── real_trading/           # 实盘预测脚本（当期选股/预测）
├── result/                 # 已跑出的策略结果（面向非技术用户查看）
└── backtest.py             # 回测入口（按你的实现方式调用）
```

---

## 🧩 自定义因子接入 -- 最常用扩展点

### Step 1：放入 CSV

1. 将因子 CSV 放到：`./factors/factor_data/`
2. 文件名与因子名称保持一致（例如 `factor_name.csv`）
3. 按 `./factors/factor.py` 中约定的格式组织索引与字段

### Step 2：写一个因子类

在代码中继承 `factors.Factor`，并在 `super().__init__()` 里定义名称等参数，然后把该因子加入因子列表即可。

---

## 📦 输出文件说明 -- 你会最常见到的两类结果

* `prediction*.csv`：每期每只股票的 **预期收益率**（用于选股/回测）
* `w*.csv`：每期每只股票的 **目标权重**（用于组合构建/回测）

回测运行记录默认保存在：

* `strategies/record/<运行时间戳_策略名>/...`

---

## 🛠️ 常见问题（FAQ）

* **Q：我没有数据库，能用吗？**
  A：可以。项目已经提供完整数据，每月更新。

* **Q：我只想看选股结果，不想跑代码？**
  A：直接看 `result/` 目录（策略说明 + 收益曲线 + 每期选股明细）。

---

## 🤝 贡献与反馈

欢迎提 Issue ，包括但不限于：

* 因子实现与验证
* 回测逻辑优化（换仓、费用、滑点、风控等）
* 数据接口适配与清洗
* 文档完善与示例补充

---

## 📄 License

MIT License（见 `LICENSE`）

---

## 📬 联系方式

* Issue：保存问题与解答
* 抖音号：72112184299

