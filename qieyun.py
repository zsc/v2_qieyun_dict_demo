#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


__version__ = "0.1.0"


_DICT_LINE_RE = re.compile(r"^(\S+)\s+(\S+)")


def is_han_char(ch: str) -> bool:
    if len(ch) != 1:
        return False
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF  # CJK Unified Ideographs Extension A
        or 0x4E00 <= cp <= 0x9FFF  # CJK Unified Ideographs
        or 0xF900 <= cp <= 0xFAFF  # CJK Compatibility Ideographs
        or 0x20000 <= cp <= 0x2A6DF  # Extension B
        or 0x2A700 <= cp <= 0x2B73F  # Extension C
        or 0x2B740 <= cp <= 0x2B81F  # Extension D
        or 0x2B820 <= cp <= 0x2CEAF  # Extension E
        or 0x2CEB0 <= cp <= 0x2EBEF  # Extension F
        or 0x2F800 <= cp <= 0x2FA1F  # Compatibility Supplement
        or 0x30000 <= cp <= 0x3134F  # Extension G
    )


def punctuation_category(ch: str) -> str:
    if len(ch) != 1:
        return ""
    cat = unicodedata.category(ch)
    return cat if cat.startswith("P") else ""


def load_pron_map(dict_path: Path) -> dict[str, list[str]]:
    pron_map: dict[str, list[str]] = {}
    try:
        with dict_path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if line in ("{", "}"):
                    continue
                lstripped = raw_line.lstrip()
                if lstripped.startswith("#") or lstripped.startswith("//"):
                    continue

                m = _DICT_LINE_RE.match(line)
                if not m:
                    continue
                han, ipa = m.group(1), m.group(2)
                if not han:
                    continue

                lst = pron_map.setdefault(han, [])
                if ipa not in lst:
                    lst.append(ipa)
    except FileNotFoundError:
        raise SystemExit(f"字典文件不存在: {dict_path}")
    except UnicodeDecodeError as e:
        raise SystemExit(f"字典文件编码错误(需要 UTF-8): {dict_path} ({e})")
    return pron_map


def read_input_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.text is not None:
        return args.text
    if args.file is not None:
        try:
            return Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            parser.error(f"输入文件不存在: {args.file}")
        except UnicodeDecodeError as e:
            parser.error(f"输入文件编码错误(需要 UTF-8): {args.file} ({e})")

    if not sys.stdin.isatty():
        return sys.stdin.read()

    parser.error("需要输入: 使用 -t/--text, -f/--file, 或管道输入")
    raise AssertionError("unreachable")


def convert_s2t(text: str) -> str:
    try:
        from opencc import OpenCC
    except Exception:
        raise SystemExit("缺少依赖: opencc-python-reimplemented (请先 pip install -r requirements.txt)")
    return OpenCC("s2t").convert(text)


def format_candidates(ipas: list[str], show_all: bool) -> tuple[str, str]:
    if not ipas:
        return "?", "?"
    primary = ipas[0]
    if not show_all or len(ipas) == 1:
        return primary, primary
    all_joined = " / ".join(ipas)
    return primary, f"{all_joined} (默认: {primary})"


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    raw_text = read_input_text(args, parser)
    converted_text = convert_s2t(raw_text)

    dict_path = Path(args.dict_path) if args.dict_path else Path(__file__).resolve().with_name("dictionary.txt")
    pron_map = load_pron_map(dict_path)

    ipa_parts: list[str] = []
    prev_was_han = False

    if args.verbose:
        print(f"输入: {raw_text}", end="" if raw_text.endswith("\n") else "\n")
        print(f"繁体: {converted_text}", end="" if converted_text.endswith("\n") else "\n")
        print("\n逐字对照:")

    for ch in converted_text:
        if not is_han_char(ch):
            ipa_parts.append(ch)
            if args.verbose:
                label = "[标点]" if punctuation_category(ch) else "[非汉字]"
                print(f"  {ch}   -> {label}")
            prev_was_han = False
            continue

        ipas = pron_map.get(ch, [])
        primary, display = format_candidates(ipas, show_all=args.multi)
        if prev_was_han:
            ipa_parts.append(" ")
        ipa_parts.append(primary)
        prev_was_han = True
        if args.verbose:
            print(f"  {ch}   -> {display}")

    ipa_str = "".join(ipa_parts)

    if not args.verbose:
        print(f"繁体: {converted_text}", end="" if converted_text.endswith("\n") else "\n")
    print(f"IPA:  {ipa_str}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qieyun.py",
        description="简转繁 + IPA 查询工具",
    )
    parser.add_argument("-t", "--text", help="输入文本")
    parser.add_argument("-f", "--file", help="输入文件")
    parser.add_argument("-d", "--dict", dest="dict_path", help="字典文件路径 (默认: dictionary.txt)")
    parser.add_argument("-m", "--multi", action="store_true", help="显示多音字所有候选")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出（字+IPA对照）")
    parser.add_argument("--version", action="version", version=f"qieyun {__version__}")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.text is not None and args.file is not None:
        parser.error("不能同时使用 -t/--text 和 -f/--file")
    return run(args, parser)


if __name__ == "__main__":
    raise SystemExit(main())
