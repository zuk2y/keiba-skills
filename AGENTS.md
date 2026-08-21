# AGENTS.md

このリポジトリで作業する人間・AIエージェント向けの開発ガイド。[agents.md](https://agents.md/) 標準に準拠する。

## リポジトリ概要

競馬に関する [Agent Skills](https://agentskills.io) 集。各スキルは `skills/<スキル名>/SKILL.md` に配置し、Agent Skills 標準に従う。

## ディレクトリ構成

- `skills/<name>/` — スキル本体。`SKILL.md`（必須）・`CHANGELOG.md`・`LICENSE`・`NOTICE`。
- `scripts/` — ビルド／リリース／検証スクリプト（Python 統一）。
- `.github/workflows/` — CI（lint）とリリース自動化。

## 開発の前提ツール

- **Python 3.x** — `scripts/*.py` と lint の実行に必要。
- **pipx** — pre-commit / ruff の実行に使う。導入例: `brew install pipx && pipx ensurepath`（macOS）／ `python3 -m pip install --user pipx`（pip 経由）。

## 開発フロー（PR ベース）

`main` への直接 push は行わない。変更は必ずブランチ＋Pull Request で入れる。

1. `main` を最新にして作業ブランチを切る（例: `git checkout -b docs/xxx` / `feat/xxx` / `fix/xxx`）。
2. 変更してコミット（pre-commit が整形・検証を実行）。
3. ブランチを push し、`gh pr create` などで PR を作成。
4. CI（Lint）が緑になったらマージ。マージ後にブランチを削除。

ブランチ名の接頭辞: `feat/`（機能）・`fix/`（修正）・`docs/`（文書）・`chore/`（雑務）。

## ローカル検証

```bash
pipx run pre-commit install          # 以後 commit 時に自動実行（推奨）
pipx run pre-commit run --all-files  # 全ファイルに手動実行
python scripts/lint_skills.py [スキル名]   # スキル単体の frontmatter + CHANGELOG 検証
```

ruff は pre-commit が自動管理するため個別インストールは不要。直接叩く場合のみ `pipx run ruff check .` / `pipx run ruff format .`。

## スキルを追加するとき

- `skills/<name>/SKILL.md` を作る。`name` はディレクトリ名と一致、小文字・数字・ハイフンのみ、64 文字以内。`description` は 1024 文字以内。`metadata.version` を持たせる。
- `skills/<name>/CHANGELOG.md` を [Keep a Changelog](https://keepachangelog.com/ja/) 形式で作り、`## [<version>]` セクションを用意する（無いとリリースノートが空になり検証で落ちる）。
- ライセンスは `LICENSE` / `NOTICE` を同梱し、frontmatter に `license` を記載。

## リリース

スキルは個別にバージョン管理する。

- タグ形式: **`<スキル名>/v<SemVer>`**（例: `racehorse-naming-ja/v0.2.0`）。版は `SKILL.md` の `metadata.version` と一致させる。
- タグ push で GitHub Actions が zip をビルドし、CHANGELOG の該当版を本文にした Release を自動公開する。

```bash
python scripts/release.py <スキル名>   # frontmatter と一致検証 → lint → タグ push
```

## コミット / PR 規約

- コミットメッセージは命令形の要約 1 行（英語）＋必要なら本文。
- PR は目的と変更点を簡潔に。関連 Issue があれば紐付ける。
- CI が緑であることをマージ条件とする。
