# 应用使用说明

> 🏁 **专为 Le Mans Ultimate 设计**

[![下载 .EXE](https://img.shields.io/badge/⬇️%20下载%20.EXE-v1.0--beta-brightgreen?style=for-the-badge)](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)

**👉 [下载 SectorFlowSetups.exe（无需 Python）](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)**

1. 打开上方链接
2. 滚动到 **Assets** 部分
3. 点击 `SectorFlowSetups.exe` 下载并运行

> 如果被 Windows 拦截：右键 → 属性 → 勾选 **取消锁定** → 确定

---

本指南说明普通用户如何一步一步使用 Sector Flow Setups。

## 1. 这个应用可以做什么

1. 实时读取 Le Mans Ultimate 的遥测数据
2. 分析赛车行为
3. 通过启发式规则和 AI 给出设定建议
4. 在不修改基础文件的情况下创建新的 .svm 设定文件
5. 根据你的圈速和反馈逐步学习

## 2. 开始前需要准备什么

### 选项 A — 使用 .exe（推荐，无需 Python）

| 要求 | 说明 |
|---|---|
| 🖥️ 系统 | Windows 10 或 11（64位） |
| 🎮 游戏 | **已安装并正在运行 Le Mans Ultimate** |
| 📁 基础文件 | LMU 的 `.svm` 设定文件 |

[在此下载 .exe](https://github.com/RomarioSantos-Oficial/SectorFlow-Setups/releases/tag/v1.0-beta)，双击运行即可。

### 选项 B — 从源码运行（开发者）

需要 Python 3.10+：

```bash
pip install -r requirements.txt
python main.py
```

## 3. 使用步骤

### 第 1 步. 启动应用

**选项 A（推荐）：** 双击 `SectorFlowSetups.exe`

**选项 B（开发者）：**
```bash
python main.py
```

### 第 2 步. 等待与游戏连接

界面顶部会显示 LMU、AI、DB 三个状态指示。

### 第 3 步. 加载基础设定

在 Setup 标签页中:

1. 点击 Load .svm
2. 选择文件
3. 等待确认消息

### 第 4 步. 上赛道跑圈

完成几圈后，应用会开始积累遥测数据。

### 第 5 步. 查看实时遥测

在 Telemetry 标签页中可以查看圈速、轮胎、燃油、天气和刹车信息。

### 第 6 步. 请求建议

有三种方式:

1. 在 Setup 聊天框输入问题
2. 点击 AI 建议按钮
3. 点击 Heuristics 按钮

### 第 7 步. 查看建议结果

建议会显示在 Setup 标签页右侧，包括调整量和安全警告。

### 第 8 步. 发送详细反馈

在 Feedback 标签页中，你可以更详细地描述转向不足、转向过度、制动、牵引力、悬挂硬度和轮胎磨损。

### 第 9 步. 创建新的设定文件

1. 点击 Create Setup
2. 选择模式
3. 选择天气条件
4. 确认创建

### 第 10 步. 编辑现有设定文件

1. 点击 Edit Setup
2. 选择 .svm 文件
3. 确认创建备份
4. 请求建议
5. 应用调整

## 4. 语言支持

应用未来可以支持英文、西班牙文、日文和中文，但目前 GUI 的文字仍然是固定的葡萄牙文。

要实现完整多语言，需要:

1. 把界面文字集中管理
2. 建立翻译文件
3. 增加语言选择功能
4. 根据所选语言切换按钮、标签和消息