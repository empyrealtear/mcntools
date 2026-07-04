# mcntools - Jar硬编码翻译工具

一个用于提取和替换 Minecraft 模组 JAR 文件中字符串的工具，灵感来源于[comeheres的mcntools](https://tieba.baidu.com/p/2190609248)，本项目完全基于Python3实现。

## 功能特性

- **字符串提取** - 从class文件常量池中提取可翻译字符串（选中预览class文件 或者 文件夹名右键预览/提取字符串）
- **智能翻译** - 支持DeepSeek（推荐）和Google翻译引擎
- **批量操作** - 提取、翻译、保存整个文件夹的字符串

## 安装指南

### 开发环境

```bash
# 克隆项目
git clone https://github.com/empyrealtear/mcntools.git
cd mcntools

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
## Windows
.venv\Scripts\activate.bat
## Linux/MacOS
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行应用

```bash
python src/main.py
```

### 打包发布

```bash
python build.py
```

打包后的可执行文件位于 `dist/mcntools.exe`。

## 使用说明

### 基本流程

1. **打开 JAR 文件** - 点击菜单栏或工具栏的打开按钮
2. **选择文件** - 在左侧文件树中选择 Class 文件或文件夹
3. **提取字符串（可选）** - 右键文件夹名"提取字符串"到jar名称的json文件中，可以复制发给AI网页版翻译后再粘贴回去并保存应用
4. **翻译字符串** - 在表格中选择条目，点击"翻译原文"，手动修改需点击"保存译文"
5. **保存修改** - 点击"保存JAR"覆盖原文件，建议备份原文件（虽然保存后的JAR里面有一份备份）

### 翻译配置

在编辑栏底部配置翻译引擎：

- **DeepSeek** - 需要 API Key，支持更精准的翻译
- **Google** - 无需 API Key，自动检测源语言

## 配置文件

应用会自动创建 `config.json` 配置文件，保存用户的偏好设置：

- 目标语言
- 翻译引擎
- 主题设置
- DeepSeek API Key（可选）

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](https://github.com/empyrealtear/mcntools/blob/master/LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 鸣谢

- 本项目受mod汉化工具mcntools的启发，特此感谢其作者[comeheres](https://www.mcmod.cn/author/37445.html)。
- 本项目使用[Trae IDE](https://www.trae.cn/)进行开发，感谢其提供的方便的开发环境。
