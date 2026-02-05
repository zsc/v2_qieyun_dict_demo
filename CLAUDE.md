# SPEC: 简转繁 + 字典查 IPA 的 Python CLI 工具

## 1. 背景与目标

有一个 `dictionary.txt`（示例片段如下），每行包含一个汉字及其读音字段（称为 "IPA"），例如第二列 `tuŋ`：

```

東      tuŋ     【端|東一|平】春方也...    0
菄      tuŋ     【端|東一|平】東風菜...    0
鶇      tuŋ     【端|東一|平】鶇鵍鳥名...  0
...

```

需要做一个 **纯 Python CLI 工具**：

- 从命令行或文件读取输入文本
- **非汉字部分保持不变**
- **汉字部分先做"简体 → 繁体"转换**
- 然后对转换后的每一个汉字，在 `dictionary.txt` 里查找对应的 IPA（第二列）
- 将结果显示在终端
- **若某个字在字典里有多个可能读音**，默认使用第一个，但可通过选项显示所有候选

---

## 2. 范围（Scope）

### 2.1 必做（In-scope）
1. 纯 Python CLI 应用，单文件 `qieyun.py` 即可
2. 加载本地同目录 `dictionary.txt`
3. 简体转繁体（使用 `opencc-python-reimplemented` 库）
4. 逐字（逐 Unicode code point）匹配汉字并查询读音列表
5. 输出：
   - 保留原输入的非汉字
   - 显示繁体字
   - 显示每个汉字对应 IPA
   - 多音字处理（默认第一音，可选显示候选）
6. 支持管道输入和文件输入

### 2.2 不做（Out-of-scope）
- 词级别分词、连读规则、变调
- 多字符词条匹配（只做单字）
- Web 界面/后端服务
- 字典编辑器

---

## 3. 输入与输出

### 3.1 输入
- 命令行参数传入文本：`-t "text"` 或 `--text "text"`
- 文件输入：`-f input.txt` 或 `--file input.txt`
- 管道输入：`echo "text" | python qieyun.py`
- `dictionary.txt`：UTF-8 文本文件，包含多行词条

### 3.2 输出（终端展示）
- **繁体化后的文本**（非汉字部分保持原样）
- 汉字逐字 IPA 显示（格式：字[IPA]）
- 完整 IPA 串输出（仅汉字 IPA 用空格分隔）

---

## 4. 字典文件格式与解析规则

### 4.1 词条格式
每个词条一行，至少包含两列：
- 第 1 列：单个汉字（可能是扩展区字）
- 第 2 列：读音字段（IPA），例如 `tuŋ`
- 后续列可忽略

### 4.2 分隔符
- 列之间由一个或多个空白字符分隔（空格或 tab）
- 正则提取前两列：`^(\S+)\s+(\S+)`

### 4.3 忽略行
以下行应跳过：
- 空行
- 仅包含 `{` 或 `}` 的行
- 以 `#` 或 `//` 开头的注释行

### 4.4 数据结构
解析后构建：
- `dict[str, list[str]] pron_map`
  - key：汉字（繁体）
  - value：IPA 列表（去重、保持出现顺序）

---

## 5. 简体转繁体（S2T）

### 5.1 方案要求
- 使用 `opencc-python-reimplemented` 库
- 模式：`s2t`（简体到繁体）

### 5.2 行为定义
- 对输入全文做一次转换，得到 `converted_text`
- 后续所有字典查找基于 `converted_text` 的字符

---

## 6. 汉字识别规则

### 6.1 汉字判断
使用 Unicode Script 属性判断：
- Python：`unicodedata` 或 `regex` 模块的 `\p{Script=Han}`
- 或使用范围判断：`\u4e00-\u9fff`（基本区）+ 扩展区

### 6.2 非汉字处理
- 所有非汉字字符原样保留
- 默认不查字典、不生成 IPA

---

## 7. CLI 接口规范

### 7.1 命令行参数

```
usage: qieyun.py [-h] [-t TEXT] [-f FILE] [-d DICT] [-m] [-v]

简转繁 + IPA 查询工具

options:
  -h, --help            show this help message and exit
  -t TEXT, --text TEXT  输入文本
  -f FILE, --file FILE  输入文件
  -d DICT, --dict DICT  字典文件路径 (默认: dictionary.txt)
  -m, --multi           显示多音字所有候选
  -v, --verbose         详细输出（字+IPA对照）
  --version             显示版本
```

### 7.2 使用示例

```bash
# 直接输入文本
python qieyun.py -t "东风菜"

# 从文件读取
python qieyun.py -f input.txt

# 管道输入
echo "abc东-123" | python qieyun.py

# 详细输出
python qieyun.py -t "东风菜" -v

# 显示多音字候选
python qieyun.py -t "行走了" -m
```

### 7.3 默认输出格式

```
$ python qieyun.py -t "abc东-123"
繁体: abc東-123
IPA:  tuŋ
```

### 7.4 详细输出格式 (`-v`)

```
$ python qieyun.py -t "abc东-123" -v
输入: abc东-123
繁体: abc東-123

逐字对照:
  a    -> [非汉字]
  b    -> [非汉字]
  c    -> [非汉字]
  東   -> tuŋ
  -    -> [非汉字]
  1    -> [非汉字]
  2    -> [非汉字]
  3    -> [非汉字]

IPA: tuŋ
```

### 7.5 多音字显示 (`-m`)

```
$ python qieyun.py -t "行走了" -m -v
输入: 行走了
繁体: 行走了

逐字对照:
  行   -> ɣaŋ / ɣeŋ / ɦaŋ (默认: ɣaŋ)
  走   -> tseu
  了   -> leu

IPA: ɣaŋ tseu leu
```

### 7.6 未收录字符
- 显示占位符 `?`
- IPA 串中输出 `?`

---

## 8. 性能与工程约束

### 8.1 性能要求
- 字典加载解析只做一次（程序启动时加载）
- 使用字典结构保证 O(1) 查询

### 8.2 依赖
- Python >= 3.8
- `opencc-python-reimplemented`（简繁转换）

---

## 9. 项目交付物

最小交付：
- `qieyun.py`（主程序）
- `dictionary.txt`（字典文件）
- `requirements.txt`（依赖列表）

建议目录：
```
/
qieyun.py
requirements.txt
dictionary.txt
```

---

## 10. 安装与运行

### 10.1 安装依赖

```bash
pip install -r requirements.txt
```

### 10.2 直接运行

```bash
python qieyun.py -t "东风菜"
```

---

## 11. 验收标准

### 11.1 基础功能
- 输入：`东风菜ABC123`
- 输出包含：`東風菜ABC123`（简转繁生效；非汉字不变）
- 对 `東`：能从字典查到 IPA：`tuŋ`

### 11.2 扩展区汉字
- 输入包含例如 `𠍀`：不应报错，若字典中有该条目应可查到

### 11.3 未收录字
- 输入字典没有的汉字：显示 `?`，不影响其他字符

### 11.4 管道支持
- `echo "test" | python qieyun.py` 正常工作

---

## 12. 测试用例

字典包含（至少）：
- `東 -> tuŋ`
- `菄 -> tuŋ`
- `鶇 -> tuŋ`
- `䍶 -> tuŋ`

测试：
1. `python qieyun.py -t "东菄鶇"`
   - 输出 IPA：`tuŋ tuŋ tuŋ`
2. `echo "abc东-123" | python qieyun.py`
   - 输出：`東` -> `tuŋ`
3. `python qieyun.py -t "𠍀X"`
   - 输出 IPA：`tuŋ`

---

## 13. 实现提示

- 字典解析只抓前两列
- `pron_map` 存储时去重
- 输入处理流程：
  1) 读取输入（参数/文件/管道）
  2) `converted_text = converter.convert(raw_text)`
  3) 遍历 `converted_text` -> 判断汉字
  4) 查 `pron_map`
  5) 格式化输出

## Gemini Added Memories
- 用 python 不用 python3
- The user's operating system is: darwin
- may use Apple Silicon MPS for acceleration
- [a meta request bout the working process] use `echo $'\a'` to notify the user when waiting for input
